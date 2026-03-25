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
        # Wrapping: go via 0 by travelling downward from 195
        hue = 195.0 - t * 175.0  # 195 → 20
        if hue < 0:
            hue += 360.0

        # Also brighten slightly under stress (value 0.7 → 1.0)
        v = 0.70 + t * 0.30
        # And saturate more under stress (saturation 0.5 → 0.9)
        s = 0.50 + t * 0.40

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


class Simulation:
    """Manages the school of Fish and runs the vectorised boids update each frame."""

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
            self.fish.append(fish)
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]
            self.pos[i] = fish.pos
            self.vel[i] = fish.vel

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

        # Re-point ALL existing fish since vstack allocates a new array
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
        # Re-point remaining fish after the copy
        for i, fish in enumerate(self.fish):
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]

    def update(self):
        n = len(self.fish)
        if n == 0:
            return

        px, py = self.pos[:, 0], self.pos[:, 1]
        vx, vy = self.vel[:, 0], self.vel[:, 1]

        # Pairwise squared distances
        cell_size = VISUAL_RANGE
        grid = {}
        for i, (x, y) in enumerate(zip(px, py)):
            key = (int(x / cell_size), int(y / cell_size))
            grid.setdefault(key, []).append(i)

        dx = np.zeros((n, n), dtype=np.float32)
        dy = np.zeros((n, n), dtype=np.float32)
        dist2 = np.full((n, n), np.inf, dtype=np.float32)

        for i in range(n):
            cx, cy = int(px[i] / cell_size), int(py[i] / cell_size)
            neighbours = []
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    neighbours += grid.get((cx + ox, cy + oy), [])
            for j in neighbours:
                if i == j:
                    continue
                ddx = px[i] - px[j]
                ddy = py[i] - py[j]
                dx[i, j] = ddx
                dy[i, j] = ddy
                dist2[i, j] = ddx * ddx + ddy * ddy

        # --- Separation ---
        sep_mask = dist2 < SEPARATION_RANGE**2
        dist_sep = np.sqrt(np.where(sep_mask, dist2, 1.0))
        w_sep = np.where(sep_mask, 1.0 / dist_sep, 0.0)
        sep_x = (dx * w_sep).sum(axis=1).astype(np.float32)
        sep_y = (dy * w_sep).sum(axis=1).astype(np.float32)

        # --- Alignment & Cohesion ---
        vis_mask = dist2 < VISUAL_RANGE**2
        count = vis_mask.sum(axis=1).astype(np.float32)
        safe = count > 0

        ali_x = np.zeros(n, dtype=np.float32)
        ali_y = np.zeros(n, dtype=np.float32)
        coh_x = np.zeros(n, dtype=np.float32)
        coh_y = np.zeros(n, dtype=np.float32)

        ali_x[safe] = (vx[np.newaxis, :] * vis_mask).sum(axis=1)[safe] / count[safe]
        ali_y[safe] = (vy[np.newaxis, :] * vis_mask).sum(axis=1)[safe] / count[safe]
        coh_x[safe] = (px[np.newaxis, :] * vis_mask).sum(axis=1)[safe] / count[
            safe
        ] - px[safe]
        coh_y[safe] = (py[np.newaxis, :] * vis_mask).sum(axis=1)[safe] / count[
            safe
        ] - py[safe]

        ali_len = np.sqrt(ali_x**2 + ali_y**2)
        ali_len = np.where(ali_len > 0, ali_len, 1.0)
        ali_x /= ali_len
        ali_y /= ali_len

        # --- Soft boundary ---
        turn_x = np.zeros(n, dtype=np.float32)
        turn_y = np.zeros(n, dtype=np.float32)
        nl = px < TURN_MARGIN
        nr = px > WIDTH - TURN_MARGIN
        nt = py < TURN_MARGIN
        nb = py > HEIGHT - TURN_MARGIN
        turn_x[nl] += TURN_FORCE * (TURN_MARGIN - px[nl]) / TURN_MARGIN
        turn_x[nr] -= TURN_FORCE * (px[nr] - (WIDTH - TURN_MARGIN)) / TURN_MARGIN
        turn_y[nt] += TURN_FORCE * (TURN_MARGIN - py[nt]) / TURN_MARGIN
        turn_y[nb] -= TURN_FORCE * (py[nb] - (HEIGHT - TURN_MARGIN)) / TURN_MARGIN

        # --- Combined force ---
        fx = (
            sep_x * SEP_WEIGHT
            + ali_x * ALI_WEIGHT * 0.3
            + coh_x * COH_WEIGHT * 0.001
            + turn_x
        ) * 0.5
        fy = (
            sep_y * SEP_WEIGHT
            + ali_y * ALI_WEIGHT * 0.3
            + coh_y * COH_WEIGHT * 0.001
            + turn_y
        ) * 0.5

        # Push computed forces back into each Fish, then let it move itself
        for i, fish in enumerate(self.fish):
            fish.apply_force(float(fx[i]), float(fy[i]))
            fish.move()

    def draw(self, surface: pygame.Surface):
        for fish in self.fish:
            fish.draw(surface)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boids — Fish School Simulation")
    clock = pygame.time.Clock()

    sim = Simulation(NUM_FISH)
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

        sim.update()

        # Fade trail
        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen)

        if show_help:
            lines = [
                f"Fish: {len(sim.fish)}   UP/DOWN to add/remove",
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
