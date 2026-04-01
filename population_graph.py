import pygame
import numpy as np


class PopulationGraph:
    def __init__(self, x: int, y: int, width: int = 150, height: int = 60):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.history_max = width
        self.fish_history = []
        self.predator_history = []
        self.sample_counter = 0
        self.sample_rate = 10

    def update(self, fish_count: int, predator_count: int):
        self.sample_counter += 1
        if self.sample_counter >= self.sample_rate:
            self.fish_history.append(fish_count)
            self.predator_history.append(predator_count)
            self.sample_counter = 0

            if len(self.fish_history) > self.history_max:
                self.fish_history.pop(0)
                self.predator_history.pop(0)

    def draw(self, surface: pygame.Surface):
        font = pygame.font.SysFont("monospace", 10)

        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg.fill((15, 25, 40, 180))
        surface.blit(bg, (self.x, self.y))

        pygame.draw.rect(
            surface,
            (50, 70, 100),
            (self.x, self.y, self.width, self.height),
            width=1,
        )

        if len(self.fish_history) < 2:
            return

        max_fish = max(max(self.fish_history), 100)

        fish_points = []
        predator_points = []

        for i, (fish_count, pred_count) in enumerate(
            zip(self.fish_history, self.predator_history)
        ):
            px = self.x + i
            fish_py = (
                self.y + self.height - int((fish_count / max_fish) * (self.height - 10))
            )
            pred_py = (
                self.y + self.height - int((pred_count / max_fish) * (self.height - 10))
            )
            fish_points.append((px, fish_py))
            predator_points.append((px, pred_py))

        if len(fish_points) >= 2:
            pygame.draw.lines(surface, (80, 180, 220), False, fish_points, 2)
        if len(predator_points) >= 2:
            pygame.draw.lines(surface, (220, 80, 80), False, predator_points, 2)

        current_fish = self.fish_history[-1] if self.fish_history else 0
        current_pred = self.predator_history[-1] if self.predator_history else 0

        fish_label = font.render(str(current_fish), True, (80, 180, 220))
        pred_label = font.render(str(current_pred), True, (220, 80, 80))

        surface.blit(fish_label, (self.x + 2, self.y + 2))
        surface.blit(pred_label, (self.x + self.width - 20, self.y + 2))

        title = font.render("Pop", True, (140, 160, 180))
        surface.blit(title, (self.x + self.width // 2 - 10, self.y + self.height - 12))
