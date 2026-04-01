# =============================================================================
# Window / Screen
# =============================================================================
WIDTH, HEIGHT = 900, 650

# =============================================================================
# Fish - Boids Behavior
# =============================================================================
NUM_FISH = 120

# Speed
MAX_SPEED = 3.5
MIN_SPEED = 1.5

# Flocking ranges
VISUAL_RANGE = 70  # How far fish can see neighbors
SEPARATION_RANGE = 25  # Minimum comfortable distance

# Flocking weights
SEP_WEIGHT = 1.8  # Separation force strength
ALI_WEIGHT = 1.0  # Alignment force strength
COH_WEIGHT = 1.0  # Cohesion force strength

# Fleeing from predators
FLEE_RANGE = 120  # How far fish can sense predators
FLEE_WEIGHT = 5.0  # How strongly fish steer away

# Boundary handling
TURN_MARGIN = 80  # Soft boundary margin
TURN_FORCE = 0.4  # How hard fish turn away from edges

# =============================================================================
# Fish - Survival & Reproduction
# =============================================================================
EAT_RANGE = 15  # Radius within which predator eats a fish
REPRODUCE_RANGE = 30  # Distance at which fish can reproduce
REPRODUCE_CHANCE = 0.002  # Chance per nearby pair per frame
RESPAWN_THRESHOLD = 5  # Respawn fish when count drops below this
FISH_PER_RESPAWN = 5  # How many fish to respawn

# Population limits
MAX_FISH = 400

# =============================================================================
# Predator - Behavior
# =============================================================================
PRED_SEPARATION_RANGE = 50  # Predators try to stay apart from each other

# Patrol mode
PRED_PATROL_RADIUS = 100  # Size of patrol circle
PRED_PATROL_CHASE_RADIUS = 150  # Distance at which predator switches to chase
PATROL_SPEED_FACTOR = 0.6  # Patrol speed relative to chase speed

# =============================================================================
# Predator - Survival & Reproduction
# =============================================================================
PRED_STARVE_TIME = 10.0  # Seconds before predator dies from hunger
PRED_FISH_PER_PERIOD = 3  # Fish needed per starve period to survive
FISH_TO_SPAWN_PREDATOR = 20  # Fish eaten to trigger new predator
MAX_PREDATORS = 5

# =============================================================================
# Visuals
# =============================================================================
FISH_LENGTH = 8
FISH_WIDTH = 3
BG_COLOR = (10, 22, 40)
TRAIL_ALPHA = 60  # 0-255, higher = shorter trails
