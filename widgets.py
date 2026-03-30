import pygame
import pygame_widgets
from pygame_widgets.slider import Slider
from entities import Predator
from constants import (
    VISUAL_RANGE,
    SEPARATION_RANGE,
    FLEE_RANGE,
    FLEE_WEIGHT,
    REPRODUCE_CHANCE,
)


class SliderController:
    def __init__(self, x: int, y: int, sim=None):
        self.x = x
        self.y = y
        self.panel_width = 220
        self.panel_height = 400
        self.visible = False
        self.sim = sim
        self._widgets = pygame_widgets.WidgetHandler()
        self.font = pygame.font.SysFont("monospace", 13)

        self.sliders = []
        self.label_texts = [
            f"Speed: {Predator.PRED_SPEED:.1f}",
            f"Visual Range: {VISUAL_RANGE}",
            f"Separation: {SEPARATION_RANGE}",
            f"Flee Range: {FLEE_RANGE}",
            f"Flee Weight: {FLEE_WEIGHT:.1f}",
            f"Reproduce: {REPRODUCE_CHANCE:.4f}",
        ]
        self.label_y_offsets = []
        y_offset = 50
        spacing = 45

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=0.5,
                max=5.0,
                step=0.1,
                initial=Predator.PRED_SPEED,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=30,
                max=150,
                step=5,
                initial=VISUAL_RANGE,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=10,
                max=50,
                step=1,
                initial=SEPARATION_RANGE,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=50,
                max=200,
                step=5,
                initial=FLEE_RANGE,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=1.0,
                max=10.0,
                step=0.1,
                initial=FLEE_WEIGHT,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                200,
                16,
                min=0.0,
                max=0.01,
                step=0.0005,
                initial=REPRODUCE_CHANCE,
                colour=(70, 90, 110),
                handleColour=(150, 180, 200),
            )
        )
        self.label_y_offsets.append(y_offset)
        y_offset += spacing

        self.panel_height = y_offset + 15

        for slider in self.sliders:
            slider.hide()
            self._widgets.addWidget(slider)

    def toggle(self):
        self.visible = not self.visible
        for slider in self.sliders:
            if self.visible:
                slider.show()
            else:
                slider.hide()

    def update(self, events):
        if self.visible:
            pygame_widgets.update(events)

    def apply_to_simulation(self):
        import constants

        Predator.PRED_SPEED = self.sliders[0].getValue()
        if self.sim:
            for pred in self.sim.predators:
                pred.speed = Predator.PRED_SPEED

        constants.VISUAL_RANGE = self.sliders[1].getValue()
        constants.SEPARATION_RANGE = self.sliders[2].getValue()
        constants.FLEE_RANGE = self.sliders[3].getValue()
        constants.FLEE_WEIGHT = self.sliders[4].getValue()
        constants.REPRODUCE_CHANCE = self.sliders[5].getValue()

        self.label_texts = [
            f"Speed: {Predator.PRED_SPEED:.1f}",
            f"Visual Range: {int(constants.VISUAL_RANGE)}",
            f"Separation: {int(constants.SEPARATION_RANGE)}",
            f"Flee Range: {int(constants.FLEE_RANGE)}",
            f"Flee Weight: {constants.FLEE_WEIGHT:.1f}",
            f"Reproduce: {constants.REPRODUCE_CHANCE:.4f}",
        ]

    def draw(self):
        if not self.visible:
            return

        panel = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        panel.fill((15, 25, 40, 220))
        pygame.display.get_surface().blit(panel, (self.x, self.y))

        pygame.draw.rect(
            pygame.display.get_surface(),
            (50, 70, 100),
            (self.x, self.y, self.panel_width, self.panel_height),
            width=2,
            border_radius=8,
        )

        title = self.font.render("Parameters", True, (180, 200, 220))
        pygame.display.get_surface().blit(title, (self.x + 10, self.y + 12))

        for i, text in enumerate(self.label_texts):
            label_surface = self.font.render(text, True, (200, 210, 220))
            label_y = self.y + self.label_y_offsets[i] - 18
            pygame.display.get_surface().blit(label_surface, (self.x + 12, label_y))

        for slider in self.sliders:
            slider.draw()
