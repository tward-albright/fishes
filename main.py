import sys
import pygame
from constants import WIDTH, HEIGHT, NUM_FISH, BG_COLOR, TRAIL_ALPHA
from entities import Predator
from simulation import Simulation
from widgets import SliderController
from population_graph import PopulationGraph


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boids — Fish School Simulation")
    clock = pygame.time.Clock()

    sim = Simulation(NUM_FISH)
    sim.predators.append(Predator())

    font = pygame.font.SysFont("monospace", 13)
    show_help = True
    show_patrol = False
    slider_panel = SliderController(WIDTH - 220, 50, sim)
    pop_graph = PopulationGraph(12, HEIGHT - 75, 150, 60)

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

        slider_panel.update(events)

        dt = clock.tick(60) / 1000.0
        sim.update(dt)
        slider_panel.apply_to_simulation()
        pop_graph.update(len(sim.fish), len(sim.predators))

        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill(BG_COLOR)
        fade.set_alpha(TRAIL_ALPHA)
        screen.blit(fade, (0, 0))

        sim.draw(screen, show_patrol)
        slider_panel.draw()
        pop_graph.draw(screen)

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
