import numpy as np
import pygame
from constants import (
    WIDTH,
    HEIGHT,
    TURN_MARGIN,
    MAX_SPEED,
    MIN_SPEED,
    FISH_LENGTH,
    FISH_WIDTH,
    PRED_STARVE_TIME,
    PRED_FISH_PER_PERIOD,
    PRED_SEPARATION_RANGE,
    PRED_PATROL_RADIUS,
    PRED_PATROL_CHASE_RADIUS,
    PATROL_SPEED_FACTOR,
    PRED_SPEED,
    EAT_RANGE,
    FLEE_RANGE,
)


class DeathEffect:
    def __init__(self, pos: np.ndarray):
        self.pos = pos.copy()
        self.angle = np.random.uniform(0, 2 * np.pi)
        self.lifetime = 0.0
        self.max_lifetime = 0.5

    def update(self, dt: float):
        self.lifetime += dt
        self.angle += dt * 8

    def is_done(self) -> bool:
        return self.lifetime >= self.max_lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.lifetime / self.max_lifetime
        alpha = int(255 * (1 - progress))
        radius = int(5 + progress * 25)

        center = (int(self.pos[0]), int(self.pos[1]))

        temp_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        color = (220, 80, 60, alpha)

        points = []
        for i in range(8):
            angle = self.angle + i * (np.pi / 4)
            r = radius * (0.3 + (1 - progress) * 0.7)
            x = radius + 2 + int(np.cos(angle) * r)
            y = radius + 2 + int(np.sin(angle) * r)
            points.append((x, y))

        pygame.draw.polygon(temp_surface, color, points)

        inner_radius = int(radius * 0.3 * progress)
        if inner_radius > 0:
            pygame.draw.circle(
                temp_surface,
                (255, 200, 150, alpha),
                (radius + 2, radius + 2),
                inner_radius,
            )

        surface.blit(temp_surface, (center[0] - radius - 2, center[1] - radius - 2))


class Fish:
    def __init__(self, idx: int = 0):
        self.idx = idx
        self.pos = np.zeros(2, dtype=np.float32)
        self.vel = np.zeros(2, dtype=np.float32)
        self.hue = np.random.uniform(170, 220)
        self.color = self._hsv_to_rgb(self.hue, 0.65, 0.8)
        self.force_magnitude = 0.0

    @staticmethod
    def _hsv_to_rgb(hue: float, s: float, v: float) -> tuple:
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
        FORCE_MAX = 1.2
        SMOOTHING = 0.15

        magnitude = float(np.sqrt(fx * fx + fy * fy))
        self.force_magnitude += SMOOTHING * (magnitude - self.force_magnitude)

        t = min(self.force_magnitude / FORCE_MAX, 1.0)

        hue = 195.0 - t * 175.0
        if hue < 0:
            hue += 360.0

        v = 0.70 + t * 0.30
        s = 0.50 + t * 0.40

        self.color = self._hsv_to_rgb(hue, s, v)

    def apply_force(self, fx: float, fy: float):
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
            np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * PRED_SPEED
        )
        self.fish_eaten = 0
        self.starve_timer = 0.0
        self.dead = False
        self.speed = PRED_SPEED
        self.patrol_center = self.pos.copy()
        self.patrol_angle = np.random.uniform(0, 2 * np.pi)
        self.mode = "patrol"

    def update(self, fish_pos: np.ndarray, dt: float, other_preds: list | None = None):
        self.starve_timer += dt
        if self.starve_timer >= PRED_STARVE_TIME:
            if self.fish_eaten < PRED_FISH_PER_PERIOD:
                self.dead = True
            else:
                self.fish_eaten = 0
                self.starve_timer = 0.0

        direction = np.zeros(2, dtype=np.float32)
        sep_dir = np.zeros(2, dtype=np.float32)
        nearest_dist = float("inf")

        if len(fish_pos) > 0:
            diffs = fish_pos - self.pos
            dists = np.linalg.norm(diffs, axis=1)
            nearest_idx = np.argmin(dists)
            nearest_dist = dists[nearest_idx]
            dir_to_fish = diffs[nearest_idx]
            length = float(np.linalg.norm(dir_to_fish))
            if length > 0:
                direction = (dir_to_fish / length).astype(np.float32)

        if nearest_dist < PRED_PATROL_CHASE_RADIUS:
            self.mode = "chase"
        elif nearest_dist > PRED_PATROL_CHASE_RADIUS * 1.5:
            self.mode = "patrol"

        if self.mode == "patrol":
            self.patrol_angle += dt * 1.5
            target = (
                self.patrol_center
                + np.array(
                    [np.cos(self.patrol_angle), np.sin(self.patrol_angle)],
                    dtype=np.float32,
                )
                * PRED_PATROL_RADIUS
            )
            to_target = target - self.pos
            length = float(np.linalg.norm(to_target))
            if length > 0:
                direction = (to_target / length).astype(np.float32)
            speed = self.speed * PATROL_SPEED_FACTOR
        else:
            speed = self.speed

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
            self.vel = (combined / length * speed).astype(np.float32)

        self.pos += self.vel
        if self.pos[0] < -10:
            self.pos[0] = WIDTH + 10
        elif self.pos[0] > WIDTH + 10:
            self.pos[0] = -10
        if self.pos[1] < -10:
            self.pos[1] = HEIGHT + 10
        elif self.pos[1] > HEIGHT + 10:
            self.pos[1] = -10

    def draw(self, surface: pygame.Surface, show_patrol: bool = False):
        x, y = float(self.pos[0]), float(self.pos[1])
        angle = float(np.arctan2(self.vel[1], self.vel[0]))
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        if self.mode == "patrol":
            color = (180, 100, 50)
            if show_patrol:
                pygame.draw.circle(
                    surface,
                    (60, 60, 80),
                    (int(self.patrol_center[0]), int(self.patrol_center[1])),
                    PRED_PATROL_RADIUS,
                    1,
                )
        else:
            color = (220, 60, 60)

        tip = (int(x + cos_a * 12), int(y + sin_a * 12))
        left = (int(x - cos_a * 6 - sin_a * 5), int(y - sin_a * 6 + cos_a * 5))
        tail = (int(x - cos_a * 5), int(y - sin_a * 5))
        right = (int(x - cos_a * 6 + sin_a * 5), int(y - sin_a * 6 - cos_a * 5))

        pygame.draw.polygon(surface, color, [tip, left, tail, right])
