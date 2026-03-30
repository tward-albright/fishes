# fishes

A boids-based predator and prey fish simulation using Pygame.

## Features

### School Behavior
- Boids algorithm for realistic flocking behavior
- Fish flee when predators approach
- Natural reproduction when fish are close to each other
- Visual feedback: fish change color when stressed

### Predator Behavior
- Patrol mode: predators circle when no fish nearby
- Chase mode: predators pursue nearest fish
- Predators eat fish within catch radius
- Predators reproduce when well-fed (after eating 20 fish)
- Predators starve if they don't eat enough fish within a time period

### Controls
- `UP/DOWN` - Add/remove 20 fish
- `P` - Add a predator
- `[ / ]` - Decrease/increase predator speed
- `S` - Toggle parameter sliders
- `C` - Toggle predator patrol circle visualization
- `H` - Toggle help overlay
- `ESC` - Quit

### Parameters (adjustable via sliders)
- **Speed** - Predator swim speed
- **Visual Range** - How far fish can see neighbors
- **Separation** - Minimum comfortable distance between fish
- **Flee Range** - How far fish can sense predators
- **Flee Weight** - How strongly fish flee from predators
- **Reproduce** - Chance of fish reproduction per nearby pair

## Installation

```bash
source .venv/bin/activate
python main.py
```

Requires: pygame, scipy, pygame-widgets
