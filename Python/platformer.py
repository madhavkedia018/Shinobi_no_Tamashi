import pygame
import sys

pygame.init()

# Window settings
WIDTH, HEIGHT = 800, 500
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Platformer Game")

clock = pygame.time.Clock()

# Colors
WHITE = (255,255,255)
BLACK = (0,0,0)
GREEN = (50,200,50)
BLUE = (50,50,200)
RED = (200,50,50)
YELLOW = (255,255,0)

# Player constants
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 50
GRAVITY = 0.6
JUMP_POWER = -12
MOVE_SPEED = 5

# Camera offset
camera_x = 0


# ============================
# Player Class
# ============================
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vel_y = 0
        self.on_ground = False
        self.score = 0

    def update(self, platforms):
        # Gravity
        self.vel_y += GRAVITY

        # Vertical movement
        self.rect.y += self.vel_y

        # Collision with platforms
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0:  # falling
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # jumping up into platform
                    self.rect.top = p.bottom
                    self.vel_y = 0

    def move(self, dx):
        self.rect.x += dx


# ============================
# Enemy Class
# ============================
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.speed = 2

    def update(self):
        self.rect.x += self.speed
        # Patrol behavior
        if self.rect.x < 200 or self.rect.x > 900:
            self.speed *= -1


# ============================
# Collectible (coin)
# ============================
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)

    def draw(self, surface, cam_x):
        pygame.draw.rect(surface, YELLOW, (self.rect.x - cam_x, self.rect.y, 20, 20))


# ============================
# Level Data
# ============================
platforms = [
    pygame.Rect(0, 450, 2000, 50),     # Ground
    pygame.Rect(300, 350, 150, 20),
    pygame.Rect(600, 280, 150, 20),
    pygame.Rect(900, 320, 150, 20),
]

coins = [
    Coin(350, 320),
    Coin(650, 250),
    Coin(950, 290),
]

enemies = [
    Enemy(500, 410),
    Enemy(1100, 410)
]

player = Player(100, 300)


# ============================
# Game Loop
# ============================
running = True
while running:
    clock.tick(60)
    window.fill((120,180,255))   # Sky blue background

    # -------------------------
    # Input
    # -------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    dx = 0
    if keys[pygame.K_LEFT]:
        dx = -MOVE_SPEED
    if keys[pygame.K_RIGHT]:
        dx = MOVE_SPEED

    # Jump
    if keys[pygame.K_SPACE] and player.on_ground:
        player.vel_y = JUMP_POWER

    # Move horizontally first
    player.move(dx)

    # Update player (gravity + vertical collision)
    player.update(platforms)

    # Update camera (follow player)
    camera_x = player.rect.x - WIDTH//2
    if camera_x < 0:
        camera_x = 0

    # -------------------------
    # Coin collection
    # -------------------------
    for c in coins[:]:
        if player.rect.colliderect(c.rect):
            coins.remove(c)
            player.score += 1

    # -------------------------
    # Enemy update + collision
    # -------------------------
    for e in enemies:
        e.update()
        if player.rect.colliderect(e.rect):
            print("You Died!")
            running = False

    # -------------------------
    # Draw platforms
    # -------------------------
    for p in platforms:
        pygame.draw.rect(window, GREEN, (p.x - camera_x, p.y, p.width, p.height))

    # -------------------------
    # Draw coins
    # -------------------------
    for c in coins:
        c.draw(window, camera_x)

    # -------------------------
    # Draw enemies
    # -------------------------
    for e in enemies:
        pygame.draw.rect(window, RED, (e.rect.x - camera_x, e.rect.y, e.rect.width, e.rect.height))

    # -------------------------
    # Draw player
    # -------------------------
    pygame.draw.rect(window, BLUE, (player.rect.x - camera_x, player.rect.y, PLAYER_WIDTH, PLAYER_HEIGHT))

    # Score display
    score_text = pygame.font.SysFont(None, 40).render(f"Score: {player.score}", True, BLACK)
    window.blit(score_text, (10,10))

    pygame.display.update()

pygame.quit()
sys.exit()
