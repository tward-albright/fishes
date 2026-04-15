import sys
import time
import pygame
from PyQt5.QtWidgets import QApplication
from constants import WIDTH, HEIGHT, NUM_FISH, BG_COLOR, TRAIL_ALPHA, PRED_SPEED
from entities import Predator
from simulation import Simulation
from control_window import ControlWindow


def main():
    global qt_app
    pygame.init()

    qt_app = QApplication(sys.argv)

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boids — Fish School Simulation")
    clock = pygame.time.Clock()

    sim = Simulation(NUM_FISH)
    sim.predators.append(Predator())

    current_pred_speed = PRED_SPEED

    control = ControlWindow(sim)
    control.show()

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_UP:
                    sim.add_fish(20)
                if event.key == pygame.K_DOWN:
                    sim.remove_fish(20)
                if event.key == pygame.K_p:
                    sim.predators.append(Predator())
                if event.key == pygame.K_LEFTBRACKET:
                    current_pred_speed = max(0.5, current_pred_speed - 0.2)
                    for pred in sim.predators:
                        pred.speed = current_pred_speed
                if event.key == pygame.K_RIGHTBRACKET:
                    current_pred_speed = min(8.0, current_pred_speed + 0.2)
                    for pred in sim.predators:
                        pred.speed = current_pred_speed
                if event.key == pygame.K_c:
                    pass

        dt = clock.tick(60) / 1000.0
        sim.update(dt)

        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen, False)

        pygame.display.flip()

        control.sync(clock.get_fps())

        qt_app.processEvents()


if __name__ == "__main__":
    main()
