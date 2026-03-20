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
        self.pos = np.array(
            [
                np.random.uniform(TURN_MARGIN, WIDTH - TURN_MARGIN),
                np.random.uniform(TURN_MARGIN, HEIGHT - TURN_MARGIN),
            ],
            dtype=np.float32,
        )

        angle = np.random.uniform(0, 2 * np.pi)
        speed = np.random.uniform(MIN_SPEED, MAX_SPEED)
        self.vel = np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * speed

        self.hue = np.random.uniform(170, 220)
        self.color = self._hue_to_rgb(self.hue)

    @staticmethod
    def _hue_to_rgb(hue: float) -> tuple:
        """Convert a hue (degrees) with fixed saturation/value to an RGB tuple."""
        h = hue / 60.0
        s, v = 0.65, 0.80
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

    def apply_force(self, fx: float, fy: float):
        """Add a steering force and clamp speed to [MIN_SPEED, MAX_SPEED]."""
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
        self.fish: list = [Fish() for _ in range(n)]

    def add_fish(self, count: int = 20):
        self.fish.extend(Fish() for _ in range(count))

    def remove_fish(self, count: int = 20):
        del self.fish[-min(count, len(self.fish)) :]

    def _arrays(self):
        """Snapshot positions and velocities into NumPy arrays for batch computation."""
        pos = np.array([f.pos for f in self.fish], dtype=np.float32)
        vel = np.array([f.vel for f in self.fish], dtype=np.float32)
        return pos, vel

    def update(self):
        n = len(self.fish)
        if n == 0:
            return

        pos, vel = self._arrays()
        px, py = pos[:, 0], pos[:, 1]
        vx, vy = vel[:, 0], vel[:, 1]

        # Pairwise squared distances
        dx = px[:, np.newaxis] - px[np.newaxis, :]
        dy = py[:, np.newaxis] - py[np.newaxis, :]
        dist2 = dx * dx + dy * dy
        np.fill_diagonal(dist2, np.inf)

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
