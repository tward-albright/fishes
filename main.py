import sys

import numpy as np
import pygame

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

    def update(self, fish_pos: np.ndarray):
        """Steer toward the closest fish."""
        if len(fish_pos) == 0:
            return
        diffs = fish_pos - self.pos  # (n, 2)
        dists = np.linalg.norm(diffs, axis=1)
        nearest = np.argmin(dists)
        direction = diffs[nearest]
        length = float(np.linalg.norm(direction))
        if length > 0:
            self.vel = (direction / length * self.PRED_SPEED).astype(np.float32)

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

    def update(self):
        n = len(self.fish)
        if n == 0:
            return

        px, py = self.pos[:, 0], self.pos[:, 1]
        vx, vy = self.vel[:, 0], self.vel[:, 1]

        # Build spatial grid
        cell_size = VISUAL_RANGE
        grid: dict = {}
        for i in range(n):
            key = (int(px[i] / cell_size), int(py[i] / cell_size))
            grid.setdefault(key, []).append(i)

        fx = np.zeros(n, dtype=np.float32)
        fy = np.zeros(n, dtype=np.float32)
        SEP2 = SEPARATION_RANGE**2
        VIS2 = VISUAL_RANGE**2
        FLEE2 = FLEE_RANGE**2

        for i in range(n):
            xi, yi = float(px[i]), float(py[i])
            cx, cy = int(xi / cell_size), int(yi / cell_size)

            sep_fx = sep_fy = 0.0
            ali_vx = ali_vy = 0.0
            coh_px = coh_py = 0.0
            vis_count = 0

            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for j in grid.get((cx + ox, cy + oy), ()):
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

            # Soft boundary
            turn_fx = turn_fy = 0.0
            if xi < TURN_MARGIN:
                turn_fx += TURN_FORCE * (TURN_MARGIN - xi) / TURN_MARGIN
            elif xi > WIDTH - TURN_MARGIN:
                turn_fx -= TURN_FORCE * (xi - (WIDTH - TURN_MARGIN)) / TURN_MARGIN
            if yi < TURN_MARGIN:
                turn_fy += TURN_FORCE * (TURN_MARGIN - yi) / TURN_MARGIN
            elif yi > HEIGHT - TURN_MARGIN:
                turn_fy -= TURN_FORCE * (yi - (HEIGHT - TURN_MARGIN)) / TURN_MARGIN

            # Flee from predators
            flee_fx = flee_fy = 0.0
            for pred in self.predators:
                ddx = xi - float(pred.pos[0])
                ddy = yi - float(pred.pos[1])
                d2 = ddx * ddx + ddy * ddy
                if d2 < FLEE2 and d2 > 0:
                    inv = 1.0 / d2**0.5
                    flee_fx += ddx * inv
                    flee_fy += ddy * inv

            fx[i] = (
                sep_fx * SEP_WEIGHT
                + ali_vx * ALI_WEIGHT * 0.3
                + coh_fx * COH_WEIGHT * 0.001
                + turn_fx
                + flee_fx * FLEE_WEIGHT
            ) * 0.5
            fy[i] = (
                sep_fy * SEP_WEIGHT
                + ali_vy * ALI_WEIGHT * 0.3
                + coh_fy * COH_WEIGHT * 0.001
                + turn_fy
                + flee_fy * FLEE_WEIGHT
            ) * 0.5

        for i, fish in enumerate(self.fish):
            fish.apply_force(float(fx[i]), float(fy[i]))
            fish.move()

        for pred in self.predators:
            pred.update(self.pos)

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

        sim.update()

        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen)

        if show_help:
            lines = [
                f"Fish: {len(sim.fish)}   Predators: {len(sim.predators)}",
                "UP/DOWN — add/remove fish   P — add predator",
                "H — toggle this help   ESC — quit",
            ]
            for i, line in enumerate(lines):
                txt = font.render(line, True, (100, 150, 200))
                screen.blit(txt, (12, 10 + i * 18))

        fps_txt = font.render(f"FPS: {clock.get_fps():.0f}", True, (60, 90, 130))
        screen.blit(fps_txt, (WIDTH - 80, 10))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
