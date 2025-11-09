import pygame, sys

pygame.init()

# Window
WIDTH, HEIGHT = 800, 500
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Platformer Animated")

clock = pygame.time.Clock()

# Colors
WHITE=(255,255,255); BLACK=(0,0,0)
GREEN=(50,200,50); BLUE=(80,80,255)
RED=(200,50,50); YELLOW=(255,255,0)
SKY=(135,206,235)

# Player constants
GRAVITY = 0.6
JUMP_POWER = -13
MOVE_SPEED = 5


# ============================
# BUTTON CLASS
# ============================
class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x,y,w,h)
        self.text = text

    def draw(self, surf):
        pygame.draw.rect(surf, (240,240,240), self.rect)
        pygame.draw.rect(surf, BLACK, self.rect, 3)
        font = pygame.font.SysFont(None, 28)
        img = font.render(self.text, True, BLACK)
        surf.blit(img, (self.rect.x + 10, self.rect.y + 8))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)


# Buttons
pause_btn = Button(10, 50, 120, 40, "PAUSE")
resume_btn = Button(10, 100, 120, 40, "RESUME")
quit_btn = Button(10, 150, 120, 40, "QUIT")


# ============================
# LOAD SPRITES (optional)
# ============================
def load_sprite_sheet(path, frame_width, frame_height):
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except:
        return None

    frames = []
    sheet_width = sheet.get_width() // frame_width

    for i in range(sheet_width):
        frame = sheet.subsurface((i*frame_width, 0, frame_width, frame_height))
        frames.append(frame)
    return frames


# Try loading animation frames
idle_frames = load_sprite_sheet("idle.png", 48, 48)
run_frames  = load_sprite_sheet("run.png", 48, 48)
jump_frame  = load_sprite_sheet("jump.png", 48, 48)
use_sprites = idle_frames is not None and run_frames is not None and jump_frame is not None


# ============================
# Player Class
# ============================
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 50)
        self.vel_y = 0
        self.on_ground = False

        # Animation
        self.frame = 0
        self.frame_timer = 0
        self.state = "idle"  # "idle", "run", "jump"

    def update(self, platforms):
        # Gravity
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        # Collision vertical
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = p.bottom
                    self.vel_y = 0

        # Update animation
        self.animate()

    def move(self, dx):
        self.rect.x += dx

    def animate(self):
        # Set animation state
        if not self.on_ground:
            self.state = "jump"
        else:
            if pygame.key.get_pressed()[pygame.K_LEFT] or pygame.key.get_pressed()[pygame.K_RIGHT]:
                self.state = "run"
            else:
                self.state = "idle"

        # Animation frame timer
        self.frame_timer += 1
        if self.frame_timer >= 8:
            self.frame_timer = 0
            self.frame = (self.frame + 1) % 4  # 4 frames for idle/run

    def draw(self, surface, cam_x):
        if use_sprites:
            if self.state == "idle":
                img = idle_frames[self.frame]
            elif self.state == "run":
                img = run_frames[self.frame]
            else:
                img = jump_frame[0]

            # Flip image if moving left
            keys = pygame.key.get_pressed()
            flipped = (keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT])
            if flipped:
                img = pygame.transform.flip(img, True, False)

            surface.blit(img, (self.rect.x - cam_x, self.rect.y))
        else:
            # Fallback: colored rectangle
            pygame.draw.rect(surface, BLUE, (self.rect.x - cam_x, self.rect.y, self.rect.width, self.rect.height))


# ============================
# Enemy
# ============================
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x,y,40,40)
        self.speed = 2

    def update(self):
        self.rect.x += self.speed
        if self.rect.x < 200 or self.rect.x > 1000:
            self.speed *= -1

    def draw(self, surf, cam):
        pygame.draw.rect(surf, RED, (self.rect.x - cam, self.rect.y, 40, 40))


# ============================
# Coin
# ============================
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x,y,20,20)

    def draw(self, surf, cam):
        pygame.draw.rect(surf, YELLOW, (self.rect.x - cam, self.rect.y, 20,20))


# ============================
# Level
# ============================
platforms = [
    pygame.Rect(0, 450, 2000, 50),
    pygame.Rect(300, 350, 150, 20),
    pygame.Rect(700, 300, 150, 20),
    pygame.Rect(1100, 330, 200, 20),
]

coins = [Coin(350,320), Coin(710,270), Coin(1150,300)]
enemies = [Enemy(600,410), Enemy(1300,410)]

player = Player(50,300)
camera_x = 0
score = 0
paused = False


# ============================
# Pause Function
# ============================
def pause_screen():
    global paused

    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if quit_btn.clicked(event): pygame.quit(); sys.exit()
            if resume_btn.clicked(event): paused = False

        # Draw frozen frame
        draw_game()

        draw_text = pygame.font.SysFont(None, 50).render("PAUSED", True, BLACK)
        window.blit(draw_text, (WIDTH//2 - 80, HEIGHT//2 - 50))

        resume_btn.draw(window)
        quit_btn.draw(window)

        pygame.display.update()
        clock.tick(30)


# ============================
# Draw Everything
# ============================
def draw_game():
    window.fill(SKY)

    # Platforms
    for p in platforms:
        pygame.draw.rect(window, GREEN, (p.x - camera_x, p.y, p.width, p.height))

    # Coins
    for c in coins:
        c.draw(window, camera_x)

    # Enemies
    for e in enemies:
        e.draw(window, camera_x)

    # Player
    player.draw(window, camera_x)

    # Score
    font = pygame.font.SysFont(None, 32)
    window.blit(
        font.render(f"Score: {score}", True, BLACK),
        (10,10)
    )

    # Buttons
    pause_btn.draw(window)
    quit_btn.draw(window)


# ============================
# MAIN LOOP
# ============================
running = True
while running:
    clock.tick(60)

    # Input
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running=False

        if pause_btn.clicked(event):
            paused = True
            pause_screen()

        if quit_btn.clicked(event):
            running=False

    # Keys
    keys = pygame.key.get_pressed()

    dx = 0
    if keys[pygame.K_LEFT]: dx = -MOVE_SPEED
    if keys[pygame.K_RIGHT]: dx = MOVE_SPEED

    # UP arrow to jump
    if keys[pygame.K_UP] and player.on_ground:
        player.vel_y = JUMP_POWER

    # Move and update player
    player.move(dx)
    player.update(platforms)

    # Enemy update
    for e in enemies:
        e.update()
        if player.rect.colliderect(e.rect):
            print("GAME OVER")
            running = False

    # Collect coins
    for c in coins[:]:
        if player.rect.colliderect(c.rect):
            coins.remove(c)
            score += 1

    # Camera follows player
    camera_x = max(0, player.rect.x - WIDTH//2)

    # DRAW EVERYTHING
    draw_game()
    pygame.display.update()


pygame.quit()
sys.exit()
