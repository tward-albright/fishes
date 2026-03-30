import sys

import numpy as np
import pygame
from scipy.spatial import cKDTree

# --- Configuration ---
WIDTH, HEIGHT = 900, 650
NUM_FISH = 120
MAX_SPEED = 3.5
MIN_SPEED = 1.5
VISUAL_RANGE = 70  # how far each fish can "see"
SEPARATION_RANGE = 25  # minimum comfortable distance
SEP_WEIGHT = 1.8  # separation force strength
ALI_WEIGHT = 1.0  # alignment force strength
COH_WEIGHT = 1.0  # cohesion force strength
TURN_MARGIN = 80  # soft boundary margin
TURN_FORCE = 0.4  # how hard fish turn away from edges
FLEE_RANGE = 120  # how far a fish can sense a predator
FLEE_WEIGHT = 5.0  # how hard it steers away
EAT_RANGE = 15  # radius within which predator eats a fish
RESPAWN_THRESHOLD = 30  # respawn fish when count drops below this
FISH_PER_RESPAWN = 20  # how many fish to respawn
FISH_TO_SPAWN_PREDATOR = 20  # fish eaten to trigger new predator
MAX_PREDATORS = 20
MAX_FISH = 200
PRED_STARVE_TIME = 10.0  # seconds
PRED_FISH_PER_PERIOD = 3  # fish needed per starve period to survive
PRED_SEPARATION_RANGE = 50  # predators try to stay apart
FISH_LENGTH = 8
FISH_WIDTH = 3

BG_COLOR = (10, 22, 40)
TRAIL_ALPHA = 60  # 0-255, higher = shorter trails


class Fish:
    """A single fish with its own position, velocity, and color."""

    def __init__(self):
        self.pos = np.zeros(2, dtype=np.float32)
        self.vel = np.zeros(2, dtype=np.float32)
        self.hue = np.random.uniform(170, 220)
        self.color = self._hsv_to_rgb(self.hue, 0.65, 0.8)
        self.force_magnitude = 0.0

    @staticmethod
    def _hsv_to_rgb(hue: float, s: float, v: float) -> tuple:
        """Convert HSV (hue in degrees, s and v in 0-1) to an RGB tuple."""
        h = hue / 60.0
        hi = int(h) % 6
        f = h - int(h)
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        rgb_map = [
            (v, t, p),
            (q, v, p),
            (p, v, t),
            (p, q, v),
            (t, p, v),
            (v, p, q),
        ]
        r, g, b = rgb_map[hi]
        return (int(r * 220), int(g * 220), int(b * 220))

    def update_color_from_force(self, fx: float, fy: float):
        """Shift color along a cool-to-warm ramp based on the force magnitude.

        Low force  → calm blue/teal  (hue ~195)
        High force → stressed amber/red (hue ~20)

        The transition uses an exponential smoothing so the color eases
        toward the target rather than snapping, giving a fluid shimmer.
        """
        FORCE_MAX = 1.2  # magnitude at which color saturates to full warm
        SMOOTHING = 0.15  # 0 = no change, 1 = instant snap

        magnitude = float(np.sqrt(fx * fx + fy * fy))
        self.force_magnitude += SMOOTHING * (magnitude - self.force_magnitude)

        t = min(self.force_magnitude / FORCE_MAX, 1.0)  # 0.0 (calm) → 1.0 (stressed)

        # Interpolate hue: 195 (cool blue) → 20 (warm orange-red)
        hue = 195.0 - t * 175.0
        if hue < 0:
            hue += 360.0

        v = 0.70 + t * 0.30  # brighten under stress
        s = 0.50 + t * 0.40  # saturate under stress

        self.color = self._hsv_to_rgb(hue, s, v)

    def apply_force(self, fx: float, fy: float):
        """Add a steering force and clamp speed to [MIN_SPEED, MAX_SPEED]."""
        self.update_color_from_force(fx, fy)
        self.vel[0] += fx
        self.vel[1] += fy
        speed = float(np.sqrt(self.vel[0] ** 2 + self.vel[1] ** 2))
        if speed == 0:
            return
        if speed > MAX_SPEED:
            self.vel *= MAX_SPEED / speed
        elif speed < MIN_SPEED:
            self.vel *= MIN_SPEED / speed

    def move(self):
        """Advance position by velocity and wrap around screen edges."""
        self.pos += self.vel
        if self.pos[0] < -10:
            self.pos[0] = WIDTH + 10
        elif self.pos[0] > WIDTH + 10:
            self.pos[0] = -10
        if self.pos[1] < -10:
            self.pos[1] = HEIGHT + 10
        elif self.pos[1] > HEIGHT + 10:
            self.pos[1] = -10

    def draw(self, surface: pygame.Surface):
        """Render this fish as a small arrow-shaped polygon."""
        x, y = float(self.pos[0]), float(self.pos[1])
        angle = float(np.arctan2(self.vel[1], self.vel[0]))
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        tip = (int(x + cos_a * FISH_LENGTH), int(y + sin_a * FISH_LENGTH))
        left = (
            int(x - cos_a * FISH_LENGTH * 0.5 - sin_a * FISH_WIDTH),
            int(y - sin_a * FISH_LENGTH * 0.5 + cos_a * FISH_WIDTH),
        )
        tail = (int(x - cos_a * FISH_LENGTH * 0.4), int(y - sin_a * FISH_LENGTH * 0.4))
        right = (
            int(x - cos_a * FISH_LENGTH * 0.5 + sin_a * FISH_WIDTH),
            int(y - sin_a * FISH_LENGTH * 0.5 - cos_a * FISH_WIDTH),
        )

        pygame.draw.polygon(surface, self.color, [tip, left, tail, right])


class Predator:
    """A predator that chases the nearest fish."""

    PRED_SPEED = 2.2  # slower than fish MAX_SPEED so alert fish can escape

    def __init__(self):
        self.pos = np.array(
            [
                np.random.uniform(TURN_MARGIN, WIDTH - TURN_MARGIN),
                np.random.uniform(TURN_MARGIN, HEIGHT - TURN_MARGIN),
            ],
            dtype=np.float32,
        )
        angle = np.random.uniform(0, 2 * np.pi)
        self.vel = (
            np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * self.PRED_SPEED
        )
        self.fish_eaten = 0
        self.starve_timer = 0.0
        self.dead = False
        self.speed = Predator.PRED_SPEED

    def update(self, fish_pos: np.ndarray, dt: float, other_preds: list | None = None):
        """Steer toward the closest fish and away from other predators."""
        self.starve_timer += dt
        if self.starve_timer >= PRED_STARVE_TIME:
            if self.fish_eaten < PRED_FISH_PER_PERIOD:
                self.dead = True
            else:
                self.fish_eaten = 0
                self.starve_timer = 0.0

        direction = np.zeros(2, dtype=np.float32)
        sep_dir = np.zeros(2, dtype=np.float32)

        if len(fish_pos) > 0:
            diffs = fish_pos - self.pos  # (n, 2)
            dists = np.linalg.norm(diffs, axis=1)
            nearest = np.argmin(dists)
            dir_to_fish = diffs[nearest]
            length = float(np.linalg.norm(dir_to_fish))
            if length > 0:
                direction = (dir_to_fish / length).astype(np.float32)

        if other_preds is not None:
            for other in other_preds:
                if other is self:
                    continue
                diff = self.pos - other.pos
                dist = float(np.linalg.norm(diff))
                if 0 < dist < PRED_SEPARATION_RANGE:
                    sep_dir += diff / dist

        combined = direction + sep_dir * 0.5
        length = float(np.linalg.norm(combined))
        if length > 0:
            self.vel = (combined / length * self.speed).astype(np.float32)

        self.pos += self.vel
        if self.pos[0] < -10:
            self.pos[0] = WIDTH + 10
        elif self.pos[0] > WIDTH + 10:
            self.pos[0] = -10
        if self.pos[1] < -10:
            self.pos[1] = HEIGHT + 10
        elif self.pos[1] > HEIGHT + 10:
            self.pos[1] = -10

    def draw(self, surface: pygame.Surface):
        x, y = float(self.pos[0]), float(self.pos[1])
        angle = float(np.arctan2(self.vel[1], self.vel[0]))
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        tip = (int(x + cos_a * 12), int(y + sin_a * 12))
        left = (int(x - cos_a * 6 - sin_a * 5), int(y - sin_a * 6 + cos_a * 5))
        tail = (int(x - cos_a * 5), int(y - sin_a * 5))
        right = (int(x - cos_a * 6 + sin_a * 5), int(y - sin_a * 6 - cos_a * 5))

        pygame.draw.polygon(surface, (220, 60, 60), [tip, left, tail, right])


class Simulation:
    """Manages the school of Fish, Predators, and the boids update each frame."""

    def __init__(self, n: int):
        self.pos = np.zeros((n, 2), dtype=np.float32)
        self.vel = np.zeros((n, 2), dtype=np.float32)

        self.pos[:, 0] = np.random.uniform(TURN_MARGIN, WIDTH - TURN_MARGIN, n)
        self.pos[:, 1] = np.random.uniform(TURN_MARGIN, HEIGHT - TURN_MARGIN, n)
        angles = np.random.uniform(0, 2 * np.pi, n)
        speeds = np.random.uniform(MIN_SPEED, MAX_SPEED, n)
        self.vel[:, 0] = np.cos(angles) * speeds
        self.vel[:, 1] = np.sin(angles) * speeds

        self.fish: list = []
        for i in range(n):
            fish = Fish()
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]
            self.fish.append(fish)

        self.predators: list = []

    def add_fish(self, count: int = 20):
        n = len(self.fish)
        new_pos = np.zeros((count, 2), dtype=np.float32)
        new_vel = np.zeros((count, 2), dtype=np.float32)
        new_pos[:, 0] = np.random.uniform(TURN_MARGIN, WIDTH - TURN_MARGIN, count)
        new_pos[:, 1] = np.random.uniform(TURN_MARGIN, HEIGHT - TURN_MARGIN, count)
        angles = np.random.uniform(0, 2 * np.pi, count)
        speeds = np.random.uniform(MIN_SPEED, MAX_SPEED, count)
        new_vel[:, 0] = np.cos(angles) * speeds
        new_vel[:, 1] = np.sin(angles) * speeds

        self.pos = np.vstack([self.pos, new_pos])
        self.vel = np.vstack([self.vel, new_vel])

        for i, fish in enumerate(self.fish):
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]

        for i in range(n, n + count):
            fish = Fish()
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]
            self.fish.append(fish)

    def remove_fish(self, count: int = 20):
        count = min(count, len(self.fish))
        del self.fish[-count:]
        self.pos = self.pos[:-count].copy()
        self.vel = self.vel[:-count].copy()
        for i, fish in enumerate(self.fish):
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]

    def update(self, dt: float = 0.0):
        n = len(self.fish)
        if n == 0:
            return

        px, py = self.pos[:, 0], self.pos[:, 1]
        vx, vy = self.vel[:, 0], self.vel[:, 1]

        tree = cKDTree(self.pos)

        fx = np.zeros(n, dtype=np.float32)
        fy = np.zeros(n, dtype=np.float32)
        SEP2 = SEPARATION_RANGE**2
        VIS2 = VISUAL_RANGE**2
        FLEE2 = FLEE_RANGE**2
        EAT2 = EAT_RANGE**2
        to_eat = set()

        if self.predators:
            pred_pos = np.array([pred.pos for pred in self.predators], dtype=np.float32)
            fish_pred_diffs = self.pos[:, np.newaxis, :] - pred_pos[np.newaxis, :, :]
            fish_pred_dists_sq = np.sum(fish_pred_diffs**2, axis=2)
            eat_mask = fish_pred_dists_sq < EAT2
            flee_mask = (fish_pred_dists_sq < FLEE2) & (fish_pred_dists_sq > 0)
            flee_mask &= ~eat_mask
            to_eat.update(set(np.where(eat_mask.any(axis=1))[0]))
            flee_inv = np.zeros_like(fish_pred_dists_sq)
            valid = flee_mask & (fish_pred_dists_sq > 0)
            flee_inv[valid] = 1.0 / np.sqrt(fish_pred_dists_sq[valid])
            flee_fx = np.sum(fish_pred_diffs[:, :, 0] * flee_inv, axis=1)
            flee_fy = np.sum(fish_pred_diffs[:, :, 1] * flee_inv, axis=1)
        else:
            flee_fx = np.zeros(n, dtype=np.float32)
            flee_fy = np.zeros(n, dtype=np.float32)

        for i in range(n):
            xi, yi = float(px[i]), float(py[i])

            neighbors = tree.query_ball_point((xi, yi), VISUAL_RANGE)

            sep_fx = sep_fy = 0.0
            ali_vx = ali_vy = 0.0
            coh_px = coh_py = 0.0
            vis_count = 0

            for j in neighbors:
                if i == j:
                    continue
                ddx = xi - float(px[j])
                ddy = yi - float(py[j])
                d2 = ddx * ddx + ddy * ddy
                if d2 < SEP2 and d2 > 0:
                    inv = 1.0 / d2**0.5
                    sep_fx += ddx * inv
                    sep_fy += ddy * inv
                if d2 < VIS2:
                    ali_vx += float(vx[j])
                    ali_vy += float(vy[j])
                    coh_px += float(px[j])
                    coh_py += float(py[j])
                    vis_count += 1

            if vis_count > 0:
                ali_vx /= vis_count
                ali_vy /= vis_count
                ali_len = (ali_vx * ali_vx + ali_vy * ali_vy) ** 0.5
                if ali_len > 0:
                    ali_vx /= ali_len
                    ali_vy /= ali_len
                coh_fx = coh_px / vis_count - xi
                coh_fy = coh_py / vis_count - yi
            else:
                ali_vx = ali_vy = coh_fx = coh_fy = 0.0

            turn_fx = turn_fy = 0.0
            if xi < TURN_MARGIN:
                turn_fx += TURN_FORCE * (TURN_MARGIN - xi) / TURN_MARGIN
            elif xi > WIDTH - TURN_MARGIN:
                turn_fx -= TURN_FORCE * (xi - (WIDTH - TURN_MARGIN)) / TURN_MARGIN
            if yi < TURN_MARGIN:
                turn_fy += TURN_FORCE * (TURN_MARGIN - yi) / TURN_MARGIN
            elif yi > HEIGHT - TURN_MARGIN:
                turn_fy -= TURN_FORCE * (yi - (HEIGHT - TURN_MARGIN)) / TURN_MARGIN

            fx[i] = (
                sep_fx * SEP_WEIGHT
                + ali_vx * ALI_WEIGHT * 0.3
                + coh_fx * COH_WEIGHT * 0.001
                + turn_fx
                + float(flee_fx[i]) * FLEE_WEIGHT
            ) * 0.5
            fy[i] = (
                sep_fy * SEP_WEIGHT
                + ali_vy * ALI_WEIGHT * 0.3
                + coh_fy * COH_WEIGHT * 0.001
                + turn_fy
                + float(flee_fy[i]) * FLEE_WEIGHT
            ) * 0.5
            fy[i] = (
                sep_fy * SEP_WEIGHT
                + ali_vy * ALI_WEIGHT * 0.3
                + coh_fy * COH_WEIGHT * 0.001
                + turn_fy
                + float(flee_fy[i]) * FLEE_WEIGHT
            ) * 0.5
            fy[i] = (
                sep_fy * SEP_WEIGHT
                + ali_vy * ALI_WEIGHT * 0.3
                + coh_fy * COH_WEIGHT * 0.001
                + turn_fy
                + float(flee_fy[i]) * FLEE_WEIGHT
            ) * 0.5

        for i, fish in enumerate(self.fish):
            fish.apply_force(float(fx[i]), float(fy[i]))
            fish.move()

        if to_eat:
            survivors = [i for i in range(len(self.fish)) if i not in to_eat]
            for pred in self.predators:
                if pred.dead:
                    continue
                pred.fish_eaten += len(to_eat)
                pred.starve_timer = 0.0
            self.pos = self.pos[survivors].copy()
            self.vel = self.vel[survivors].copy()
            self.fish = [self.fish[i] for i in survivors]
            for i, fish in enumerate(self.fish):
                fish.pos = self.pos[i]
                fish.vel = self.vel[i]

        for pred in self.predators:
            pred.update(self.pos, dt, self.predators)

        self.predators = [p for p in self.predators if not p.dead]

        for pred in self.predators:
            if (
                pred.fish_eaten >= FISH_TO_SPAWN_PREDATOR
                and len(self.predators) < MAX_PREDATORS
            ):
                self.predators.append(Predator())
                pred.fish_eaten = 0

        if len(self.fish) < RESPAWN_THRESHOLD and len(self.fish) < MAX_FISH:
            count = min(FISH_PER_RESPAWN, MAX_FISH - len(self.fish))
            self.add_fish(count)

    def draw(self, surface: pygame.Surface):
        for fish in self.fish:
            fish.draw(surface)
        for pred in self.predators:
            pred.draw(surface)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boids — Fish School Simulation")
    clock = pygame.time.Clock()

    sim = Simulation(NUM_FISH)
    sim.predators.append(Predator())

    font = pygame.font.SysFont("monospace", 13)
    show_help = True

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_h:
                    show_help = not show_help
                if event.key == pygame.K_UP:
                    sim.add_fish(20)
                if event.key == pygame.K_DOWN:
                    sim.remove_fish(20)
                if event.key == pygame.K_p:
                    sim.predators.append(Predator())
                if event.key == pygame.K_LEFTBRACKET:
                    Predator.PRED_SPEED = max(0.5, Predator.PRED_SPEED - 0.2)
                    for pred in sim.predators:
                        pred.speed = Predator.PRED_SPEED
                if event.key == pygame.K_RIGHTBRACKET:
                    Predator.PRED_SPEED = min(8.0, Predator.PRED_SPEED + 0.2)
                    for pred in sim.predators:
                        pred.speed = Predator.PRED_SPEED

        dt = clock.tick(60) / 1000.0
        sim.update(dt)

        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen)

        if show_help:
            lines = [
                f"Fish: {len(sim.fish)}   Predators: {len(sim.predators)}   Speed: {Predator.PRED_SPEED:.1f}",
                "UP/DOWN — add/remove fish   P — add predator",
                "[ / ] — decrease/increase predator speed",
                "H — toggle this help   ESC — quit",
            ]
            for i, line in enumerate(lines):
                txt = font.render(line, True, (100, 150, 200))
                screen.blit(txt, (12, 10 + i * 18))

        fps_txt = font.render(f"FPS: {clock.get_fps():.0f}", True, (60, 90, 130))
        screen.blit(fps_txt, (WIDTH - 80, 10))

        pygame.display.flip()


if __name__ == "__main__":
    main()
