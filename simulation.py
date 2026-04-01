import numpy as np
from scipy.spatial import cKDTree
from entities import Fish, Predator, DeathEffect
from constants import (
    MAX_FISH,
    MIN_SPEED,
    MAX_SPEED,
    TURN_MARGIN,
    WIDTH,
    HEIGHT,
    VISUAL_RANGE,
    SEPARATION_RANGE,
    SEP_WEIGHT,
    ALI_WEIGHT,
    COH_WEIGHT,
    TURN_FORCE,
    FLEE_RANGE,
    FLEE_WEIGHT,
    EAT_RANGE,
    REPRODUCE_RANGE,
    REPRODUCE_CHANCE,
    RESPAWN_THRESHOLD,
    FISH_PER_RESPAWN,
    FISH_TO_SPAWN_PREDATOR,
    MAX_PREDATORS,
)


class Simulation:
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
        self.death_effects: list = []

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
                death_pos = self.pos[i].copy()
                self.death_effects.append(DeathEffect(death_pos))

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

        for effect in self.death_effects:
            effect.update(dt)
        self.death_effects = [e for e in self.death_effects if not e.is_done()]

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

    def draw(self, surface, show_patrol: bool = False):
        for fish in self.fish:
            fish.draw(surface)
        for effect in self.death_effects:
            effect.draw(surface)
        for pred in self.predators:
            pred.draw(surface, show_patrol)
