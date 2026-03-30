import pygame
import pygame_widgets
from pygame_widgets.slider import Slider
from pygame_widgets.textbox import TextBox
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
        self.width = 200
        self.height = 320
        self.visible = False
        self.sim = sim
        self._widgets = pygame_widgets.WidgetHandler()

        self.sliders = []
        self.labels = []
        y_offset = 50
        spacing = 45

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=0.5,
                max=5.0,
                step=0.1,
                initial=Predator.PRED_SPEED,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Speed: {Predator.PRED_SPEED:.1f}",
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=30,
                max=150,
                step=5,
                initial=VISUAL_RANGE,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Visual Range: {VISUAL_RANGE}",
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=10,
                max=50,
                step=1,
                initial=SEPARATION_RANGE,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Separation: {SEPARATION_RANGE}",
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=50,
                max=200,
                step=5,
                initial=FLEE_RANGE,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Flee Range: {FLEE_RANGE}",
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=1.0,
                max=10.0,
                step=0.1,
                initial=FLEE_WEIGHT,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Flee Weight: {FLEE_WEIGHT:.1f}",
            )
        )
        y_offset += spacing

        self.sliders.append(
            Slider(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset,
                180,
                20,
                min=0.0,
                max=0.01,
                step=0.0005,
                initial=REPRODUCE_CHANCE,
            )
        )
        self.labels.append(
            TextBox(
                pygame.display.get_surface(),
                x + 10,
                y + y_offset - 20,
                180,
                18,
                fontSize=12,
                textColour=(180, 200, 220),
                text=f"Reproduce: {REPRODUCE_CHANCE:.4f}",
            )
        )
        y_offset += spacing

        self.height = y_offset + 10

        for slider in self.sliders:
            slider.hide()
            self._widgets.addWidget(slider)
        for label in self.labels:
            label.hide()

    def toggle(self):
        self.visible = not self.visible
        for slider in self.sliders:
            if self.visible:
                slider.show()
            else:
                slider.hide()
        for label in self.labels:
            if self.visible:
                label.show()
            else:
                label.hide()

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

        self.labels[0].setText(f"Speed: {Predator.PRED_SPEED:.1f}")
        self.labels[1].setText(f"Visual Range: {int(constants.VISUAL_RANGE)}")
        self.labels[2].setText(f"Separation: {int(constants.SEPARATION_RANGE)}")
        self.labels[3].setText(f"Flee Range: {int(constants.FLEE_RANGE)}")
        self.labels[4].setText(f"Flee Weight: {constants.FLEE_WEIGHT:.1f}")
        self.labels[5].setText(f"Reproduce: {constants.REPRODUCE_CHANCE:.4f}")

    def draw(self):
        if not self.visible:
            return
        for label in self.labels:
            label.draw()
        for slider in self.sliders:
            slider.draw()
