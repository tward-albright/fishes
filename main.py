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
RESPAWN_THRESHOLD = 5  # respawn fish when count drops below this
FISH_PER_RESPAWN = 5  # how many fish to respawn
FISH_TO_SPAWN_PREDATOR = 20  # fish eaten to trigger new predator
MAX_PREDATORS = 5
MAX_FISH = 800
PRED_STARVE_TIME = 10.0  # seconds
PRED_FISH_PER_PERIOD = 3  # fish needed per starve period to survive
PRED_SEPARATION_RANGE = 50  # predators try to stay apart
PRED_PATROL_RADIUS = 100  # patrol circle size
PRED_PATROL_CHASE_RADIUS = 150  # distance at which predator switches to chase
PATROL_SPEED_FACTOR = 0.6  # patrol speed relative to chase speed
REPRODUCE_RANGE = 30  # distance at which fish can reproduce
REPRODUCE_CHANCE = 0.002  # chance per nearby pair per frame
FISH_LENGTH = 8
FISH_WIDTH = 3

BG_COLOR = (10, 22, 40)
TRAIL_ALPHA = 60  # 0-255, higher = shorter trails


class Slider:
    """A simple horizontal slider for parameter adjustment."""

    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        default_val: float,
        x: int,
        y: int,
        width: int = 150,
    ):
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = default_val
        self.x = x
        self.y = y
        self.width = width
        self.height = 20
        self.dragging = False
        self.visible = False

    def get_value(self):
        return self.value

    def set_value(self, val: float):
        self.value = max(self.min_val, min(self.max_val, val))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.visible and self.is_over(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging and self.visible:
                rel_x = event.pos[0] - self.x
                ratio = max(0, min(1, rel_x / self.width))
                self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def is_over(self, pos: tuple) -> bool:
        return (
            self.x <= pos[0] <= self.x + self.width
            and self.y <= pos[1] <= self.y + self.height
        )

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.visible:
            return

        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        knob_x = self.x + int(ratio * self.width)

        pygame.draw.rect(
            surface,
            (40, 50, 70),
            (self.x, self.y, self.width, self.height),
            border_radius=3,
        )
        pygame.draw.rect(
            surface,
            (80, 120, 180),
            (self.x, self.y, self.width, self.height),
            border_radius=3,
            width=2,
        )

        pygame.draw.circle(
            surface, (200, 200, 220), (knob_x, self.y + self.height // 2), 8
        )
        pygame.draw.circle(
            surface, (150, 170, 200), (knob_x, self.y + self.height // 2), 8, 2
        )

        label_text = font.render(
            f"{self.label}: {self.value:.2f}", True, (180, 200, 220)
        )
        surface.blit(label_text, (self.x, self.y - 18))


class SliderPanel:
    """A panel containing multiple sliders."""

    def __init__(self, x: int, y: int, sim=None):
        self.x = x
        self.y = y
        self.width = 200
        self.height = 300
        self.visible = False
        self.sliders: list[Slider] = []
        self.sim = sim
        self._setup_sliders()

    def _setup_sliders(self):
        y_offset = 10
        spacing = 45

        self.sliders.append(
            Slider(
                "Speed", 0.5, 5.0, Predator.PRED_SPEED, self.x + 10, self.y + y_offset
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                "Visual Range", 30, 150, VISUAL_RANGE, self.x + 10, self.y + y_offset
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                "Separation", 10, 50, SEPARATION_RANGE, self.x + 10, self.y + y_offset
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider("Flee Range", 50, 200, FLEE_RANGE, self.x + 10, self.y + y_offset)
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                "Flee Weight", 1.0, 10.0, FLEE_WEIGHT, self.x + 10, self.y + y_offset
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                "Reproduce", 0.0, 0.01, REPRODUCE_CHANCE, self.x + 10, self.y + y_offset
            )
        )
        y_offset += spacing

        self.height = y_offset + 30

    def toggle(self):
        self.visible = not self.visible
        for slider in self.sliders:
            slider.visible = self.visible

    def handle_event(self, event: pygame.event.Event):
        for slider in self.sliders:
            slider.handle_event(event)

    def apply_to_simulation(self):
        for slider in self.sliders:
            if slider.label == "Speed":
                Predator.PRED_SPEED = slider.get_value()
                if self.sim:
                    for pred in self.sim.predators:
                        pred.speed = Predator.PRED_SPEED
            elif slider.label == "Visual Range":
                globals()["VISUAL_RANGE"] = int(slider.get_value())
            elif slider.label == "Separation":
                globals()["SEPARATION_RANGE"] = int(slider.get_value())
            elif slider.label == "Flee Range":
                globals()["FLEE_RANGE"] = int(slider.get_value())
            elif slider.label == "Flee Weight":
                globals()["FLEE_WEIGHT"] = slider.get_value()
            elif slider.label == "Reproduce":
                globals()["REPRODUCE_CHANCE"] = slider.get_value()

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if not self.visible:
            return

        panel_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        panel_surface.fill((20, 30, 50, 230))
        surface.blit(panel_surface, (self.x, self.y))

        pygame.draw.rect(
            surface,
            (60, 90, 140),
            (self.x, self.y, self.width, self.height),
            border_radius=8,
            width=2,
        )

        title = font.render("Parameters", True, (200, 220, 240))
        surface.blit(title, (self.x + 10, self.y + 5))

        for slider in self.sliders:
            slider.draw(surface, font)


class Fish:
    """A single fish with its own position, velocity, and color."""

    def __init__(self, idx: int = 0):
        self.idx = idx
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
    """A predator that alternates between chasing fish and patrolling."""

    PRED_SPEED = 2.2

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
        self.patrol_center = self.pos.copy()
        self.patrol_angle = np.random.uniform(0, 2 * np.pi)
        self.mode = "patrol"

    def update(self, fish_pos: np.ndarray, dt: float, other_preds: list | None = None):
        """Steer toward closest fish or patrol, avoid other predators."""
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


class Simulation:
    """Manages the school of Fish, Predators, and the boids update each frame."""

    def __init__(self, n: int):
        self.pos = np.zeros((MAX_FISH, 2), dtype=np.float32)
        self.vel = np.zeros((MAX_FISH, 2), dtype=np.float32)
        self.active_count = n

        self.pos[:n, 0] = np.random.uniform(TURN_MARGIN, WIDTH - TURN_MARGIN, n)
        self.pos[:n, 1] = np.random.uniform(TURN_MARGIN, HEIGHT - TURN_MARGIN, n)
        angles = np.random.uniform(0, 2 * np.pi, n)
        speeds = np.random.uniform(MIN_SPEED, MAX_SPEED, n)
        self.vel[:n, 0] = np.cos(angles) * speeds
        self.vel[:n, 1] = np.sin(angles) * speeds

        self.fish: list = []
        for i in range(n):
            fish = Fish(i)
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]
            self.fish.append(fish)

        self.predators: list = []
        self.frame_count = 0
        self._tree = None
        self._tree_valid = False

    def add_fish(self, count: int = 20):
        count = min(count, MAX_FISH - self.active_count)
        if count <= 0:
            return
        start = self.active_count
        end = start + count

        self.pos[start:end, 0] = np.random.uniform(
            TURN_MARGIN, WIDTH - TURN_MARGIN, count
        )
        self.pos[start:end, 1] = np.random.uniform(
            TURN_MARGIN, HEIGHT - TURN_MARGIN, count
        )
        angles = np.random.uniform(0, 2 * np.pi, count)
        speeds = np.random.uniform(MIN_SPEED, MAX_SPEED, count)
        self.vel[start:end, 0] = np.cos(angles) * speeds
        self.vel[start:end, 1] = np.sin(angles) * speeds

        for i in range(start, end):
            fish = Fish(i)
            fish.pos = self.pos[i]
            fish.vel = self.vel[i]
            self.fish.append(fish)

        self.active_count = end
        self._tree_valid = False

    def remove_fish(self, count: int = 20):
        count = min(count, self.active_count)
        self.active_count -= count
        self.fish = self.fish[:-count] if count > 0 else self.fish
        self._tree_valid = False

    def update(self, dt: float = 0.0):
        if self.active_count == 0:
            return

        n = self.active_count
        px, py = self.pos[:n, 0], self.pos[:n, 1]
        vx, vy = self.vel[:n, 0], self.vel[:n, 1]

        if self._tree is None or not self._tree_valid:
            self._tree = cKDTree(self.pos[:n])
            self._tree_valid = True
        tree = self._tree

        fx = np.zeros(n, dtype=np.float32)
        fy = np.zeros(n, dtype=np.float32)
        SEP2 = SEPARATION_RANGE**2
        VIS2 = VISUAL_RANGE**2
        FLEE2 = FLEE_RANGE**2
        EAT2 = EAT_RANGE**2
        to_eat = set()

        if self.predators:
            pred_pos = np.array([pred.pos for pred in self.predators], dtype=np.float32)
            fish_pred_diffs = self.pos[:n, np.newaxis, :] - pred_pos[np.newaxis, :, :]
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

        for i, fish in enumerate(self.fish):
            fish.apply_force(float(fx[i]), float(fy[i]))
            fish.move()

        if to_eat:
            for pred in self.predators:
                if pred.dead:
                    continue
                pred.fish_eaten += len(to_eat)
                pred.starve_timer = 0.0

            to_eat_sorted = sorted(to_eat, reverse=True)
            for i in to_eat_sorted:
                last_idx = self.active_count - 1
                if i != last_idx:
                    self.pos[i] = self.pos[last_idx]
                    self.vel[i] = self.vel[last_idx]
                    self.fish[i].idx = i
                    self.fish[i].pos = self.pos[i]
                    self.fish[i].vel = self.vel[i]
                self.active_count -= 1
                self.fish.pop()
            self._tree_valid = False

        for pred in self.predators:
            pred.update(self.pos[: self.active_count], dt, self.predators)

        self.predators = [p for p in self.predators if not p.dead]

        for pred in self.predators:
            if (
                pred.fish_eaten >= FISH_TO_SPAWN_PREDATOR
                and len(self.predators) < MAX_PREDATORS
            ):
                self.predators.append(Predator())
                pred.fish_eaten = 0

        self.frame_count += 1
        if self.frame_count % 4 == 0:
            self._tree_valid = False
        if (
            self.frame_count % 4 == 0
            and self.active_count >= 2
            and self.active_count < MAX_FISH
        ):
            if self._tree is None or not self._tree_valid:
                self._tree = cKDTree(self.pos[: self.active_count])
                self._tree_valid = True
            pairs = self._tree.query_pairs(REPRODUCE_RANGE)
            for i, j in pairs:
                if self.active_count >= MAX_FISH:
                    break
                if np.random.random() < REPRODUCE_CHANCE:
                    self.pos[self.active_count] = (self.pos[i] + self.pos[j]) / 2
                    new_vel = (self.vel[i] + self.vel[j]) / 2
                    speed = np.linalg.norm(new_vel)
                    if speed > 0:
                        self.vel[self.active_count] = (
                            new_vel / speed * np.random.uniform(MIN_SPEED, MAX_SPEED)
                        )
                    else:
                        angle = np.random.uniform(0, 2 * np.pi)
                        self.vel[self.active_count] = np.array(
                            [np.cos(angle), np.sin(angle)], dtype=np.float32
                        ) * np.random.uniform(MIN_SPEED, MAX_SPEED)
                    fish = Fish(self.active_count)
                    fish.pos = self.pos[self.active_count]
                    fish.vel = self.vel[self.active_count]
                    self.fish.append(fish)
                    self.active_count += 1
                    self._tree_valid = False

        if self.active_count < RESPAWN_THRESHOLD and self.active_count < MAX_FISH:
            count = min(FISH_PER_RESPAWN, MAX_FISH - self.active_count)
            self.add_fish(count)

    def draw(self, surface: pygame.Surface, show_patrol: bool = False):
        for fish in self.fish:
            fish.draw(surface)
        for pred in self.predators:
            pred.draw(surface, show_patrol)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boids — Fish School Simulation")
    clock = pygame.time.Clock()

    sim = Simulation(NUM_FISH)
    sim.predators.append(Predator())

    font = pygame.font.SysFont("monospace", 13)
    font_small = pygame.font.SysFont("monospace", 11)
    show_help = True
    show_patrol = False
    slider_panel = SliderPanel(WIDTH - 220, 50, sim)

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
                if event.key == pygame.K_s:
                    slider_panel.toggle()
                if event.key == pygame.K_c:
                    show_patrol = not show_patrol

            slider_panel.handle_event(event)

        dt = clock.tick(60) / 1000.0
        sim.update(dt)
        slider_panel.apply_to_simulation()

        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen, show_patrol)
        slider_panel.draw(screen, font_small)

        if show_help:
            lines = [
                f"Fish: {len(sim.fish)}   Predators: {len(sim.predators)}",
                "UP/DOWN — add/remove fish   P — add predator",
                "[ / ] — predator speed   S — sliders   C — patrol circles",
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
