import pygame, sys, os, math

pygame.init()
WIDTH, HEIGHT = 960, 540
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ninja Platformer")
clock = pygame.time.Clock()

# ------------------ Settings ------------------
FPS = 60
GRAVITY = 0.6
MOVE_SPEED = 5
JUMP_POWER = -12
DOUBLE_JUMP_POWER = -11
TILE = 48

# ------------------ Load Helpers ------------------
def load_sheet(path, fw, fh):
    img = pygame.image.load(path).convert_alpha()
    frames_across = img.get_width() // fw
    frames = []
    for i in range(frames_across):
        surf = pygame.Surface((fw, fh), pygame.SRCALPHA)
        surf.blit(img, (0,0), pygame.Rect(i*fw, 0, fw, fh))
        frames.append(surf)
    return frames

def safe_load(path, fw=None, fh=None):
    if not os.path.exists(path):
        return None
    if fw and fh:
        return load_sheet(path, fw, fh)
    return pygame.image.load(path).convert_alpha()

# ------------------ Assets ------------------
IDLE = load_sheet("player_idle.png", 48, 48) or []
RUN  = load_sheet("player_run.png", 48, 48) or []
JUMP = load_sheet("player_jump.png", 48, 48) or []
DJMP = load_sheet("player_doublejump.png", 48, 48) or []
EWALK = load_sheet("enemy_walk.png", 48, 48) or []
ESTOMP = load_sheet("enemy_stomp.png", 48, 48) or []
COIN = load_sheet("coin.png", 32, 32) or []

BG_SKY = safe_load("bg_sky.png")
BG_MTN = safe_load("bg_mountains.png")
BG_TRE = safe_load("bg_trees.png")
BG_GRASS = safe_load("bg_grass.png")

# Music (WAV recommended for broad support)
try:
    pygame.mixer.music.load("bg_music.wav")
    pygame.mixer.music.set_volume(0.5)
except Exception as e:
    print("Music not loaded:", e)

# ------------------ Classes ------------------
class Parallax:
    def __init__(self):
        self.layers = [
            (BG_SKY, 0.1),
            (BG_MTN, 0.3),
            (BG_TRE, 0.6),
            (BG_GRASS, 0.9),
        ]
    def draw(self, surf, camera_x):
        surf.fill((120,180,255))
        for img, speed in self.layers:
            if not img: continue
            w = img.get_width()
            # tile horizontally
            x = - (camera_x * speed) % w
            surf.blit(img, (x - w, 0))
            surf.blit(img, (x, 0))
            surf.blit(img, (x + w, 0))

class Platform:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
    def draw(self, surf, camx):
        pygame.draw.rect(surf, (60,170,70), (self.rect.x - camx, self.rect.y, self.rect.w, self.rect.h))

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 24, 24)
        self.t = 0
    def update(self):
        self.t += 1
    def draw(self, surf, camx):
        if COIN:
            frame = COIN[(self.t//6) % len(COIN)]
            surf.blit(frame, (self.rect.x - camx - 4, self.rect.y - 4))
        else:
            pygame.draw.circle(surf, (255,215,0), (self.rect.x - camx + 12, self.rect.y + 12), 12)
    def collect(self, player):
        return self.rect.colliderect(player.rect)

class Enemy:
    def __init__(self, x, y, left_bound, right_bound):
        self.rect = pygame.Rect(x, y, 40, 44)
        self.vx = 2
        self.left = left_bound
        self.right = right_bound
        self.stomped = False
        self.t = 0
    def update(self):
        if self.stomped:
            self.t += 1
            return
        self.rect.x += self.vx
        if self.rect.x < self.left or self.rect.x > self.right:
            self.vx *= -1
    def draw(self, surf, camx):
        if self.stomped and ESTOMP:
            surf.blit(ESTOMP[0], (self.rect.x - camx - 4, self.rect.y - 4))
        elif EWALK:
            frame = EWALK[(pygame.time.get_ticks()//120) % len(EWALK)]
            flip = self.vx < 0
            img = pygame.transform.flip(frame, flip, False) if flip else frame
            surf.blit(img, (self.rect.x - camx - 4, self.rect.y - 4))
        else:
            pygame.draw.rect(surf, (200,50,50), (self.rect.x - camx, self.rect.y, self.rect.w, self.rect.h))

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 46)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.can_double = True
        self.facing_left = False
        self.state = "idle"
        self.anim_t = 0
    def handle_input(self, keys):
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_left = True
        if keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_left = False
        if keys[pygame.K_UP]:  # Up arrow = jump
            if self.on_ground:
                self.vy = JUMP_POWER
                self.on_ground = False
                self.can_double = True
            elif self.can_double:
                self.vy = DOUBLE_JUMP_POWER
                self.can_double = False
    def physics(self, platforms):
        # horizontal
        self.rect.x += self.vx
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vx > 0:
                    self.rect.right = p.rect.left
                elif self.vx < 0:
                    self.rect.left = p.rect.right
        # vertical
        self.vy += GRAVITY
        self.rect.y += self.vy
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                    self.can_double = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0
    def stomp_enemy(self, enemy):
        # if falling and feet hit enemy top -> stomp
        feet = pygame.Rect(self.rect.x+6, self.rect.bottom-6, self.rect.w-12, 8)
        head = pygame.Rect(enemy.rect.x, enemy.rect.y, enemy.rect.w, 10)
        return self.vy > 0 and feet.colliderect(head)
    def update_anim(self):
        if not self.on_ground:
            self.state = "jump"
        else:
            if self.vx != 0:
                self.state = "run"
            else:
                self.state = "idle"
        self.anim_t += 1
    def draw(self, surf, camx):
        img = None
        if self.state == "idle" and IDLE:
            img = IDLE[(self.anim_t//10) % len(IDLE)]
        elif self.state == "run" and RUN:
            img = RUN[(self.anim_t//6) % len(RUN)]
        elif self.state == "jump" and JUMP:
            # show double-jump frame if we already used it
            if not self.can_double and DJMP:
                img = DJMP[0]
            else:
                img = JUMP[0]
        if img:
            draw = pygame.transform.flip(img, self.facing_left, False)
            surf.blit(draw, (self.rect.x - camx - 4, self.rect.y - 2))
        else:
            # fallback box
            pygame.draw.rect(surf, (80,80,255), (self.rect.x - camx, self.rect.y, self.rect.w, self.rect.h))

# ------------------ Level ------------------
def build_level():
    platforms = [
        Platform(( -200, 480, 2400, 60)),   # ground
        Platform(( 200, 400, 160, 18)),
        Platform(( 420, 340, 160, 18)),
        Platform(( 700, 320, 180, 18)),
        Platform(( 980, 360, 180, 18)),
        Platform((1300, 300, 180, 18)),
        Platform((1600, 420, 220, 18)),
    ]
    coins = [
        Coin(230, 360), Coin(460, 300), Coin(740, 280),
        Coin(1010, 320), Coin(1330, 260), Coin(1650, 380)
    ]
    enemies = [
        Enemy(560, 436, 520, 780),
        Enemy(1180, 436, 1120, 1400),
        Enemy(1520, 376, 1480, 1750),
    ]
    # Level end flag
    flag_rect = pygame.Rect(2000, 420, 20, 60)
    return platforms, coins, enemies, flag_rect

# ------------------ Screens ------------------
def draw_text_center(surf, txt, size, color, y):
    font = pygame.font.SysFont(None, size)
    img = font.render(txt, True, color)
    x = (WIDTH - img.get_width())//2
    surf.blit(img, (x, y))

def main_menu():
    window.fill((15,15,25))
    draw_text_center(window, "NINJA PLATFORMER", 64, (255,255,255), 150)
    draw_text_center(window, "Press ENTER to Start", 36, (200,220,255), 260)
    draw_text_center(window, "Use Arrow Keys (← → to move, ↑ to jump/double jump)", 26, (200,200,200), 320)
    draw_text_center(window, "Stomp enemies by landing on their head", 26, (200,200,200), 350)
    pygame.display.update()
    # start music
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
    except: pass
    # wait for enter
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return

def level_intro(level_num):
    t=0
    while t<90:
        window.fill((0,0,0))
        draw_text_center(window, f"Level {level_num}", 56, (255,255,255), HEIGHT//2-40)
        pygame.display.update()
        clock.tick(FPS)
        t+=1

def game_over_screen(score):
    window.fill((10,10,20))
    draw_text_center(window, "GAME OVER", 64, (255,80,80), 160)
    draw_text_center(window, f"Score: {score}", 40, (255,255,255), 240)
    draw_text_center(window, "Press R to Retry  |  Press Q to Quit", 28, (220,220,220), 320)
    pygame.display.update()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return "retry"
                if e.key == pygame.K_q: return "quit"

def level_complete_screen(level_num, score):
    window.fill((10,20,10))
    draw_text_center(window, f"Level {level_num} Complete!", 56, (180,255,180), 160)
    draw_text_center(window, f"Score: {score}", 40, (255,255,255), 240)
    draw_text_center(window, "Press ENTER for next level", 28, (220,220,220), 320)
    pygame.display.update()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return

# ------------------ Game Loop ------------------
def run_level(level_num=1):
    parallax = Parallax()
    platforms, coins, enemies, flag_rect = build_level()
    player = Player(100, 380)
    score = 0
    camera_x = 0
    running = True
    while running:
        dt = clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        player.physics(platforms)

        # Coins
        for c in coins[:]:
            c.update()
            if c.collect(player):
                coins.remove(c)
                score += 1

        # Enemies
        for en in enemies[:]:
            en.update()
            if en.stomped:
                # remove after a bit
                if en.t > 30:
                    enemies.remove(en)
                continue
            if player.stomp_enemy(en):
                en.stomped = True
                player.vy = JUMP_POWER * 0.6  # bounce
                score += 5
            elif player.rect.colliderect(en.rect):
                return ("dead", score)

        # Level complete?
        if player.rect.colliderect(flag_rect):
            return ("complete", score)

        player.update_anim()

        # Camera follows
        camera_x = max(0, int(player.rect.centerx - WIDTH*0.5))

        # Draw
        parallax.draw(window, camera_x)
        # Platforms
        for p in platforms:
            p.draw(window, camera_x)
        # Flag
        pygame.draw.rect(window, (255,255,255), (flag_rect.x - camera_x, flag_rect.y - 40, 4, 100))
        pygame.draw.polygon(window, (255,0,0), [(flag_rect.x - camera_x+4, flag_rect.y - 40),
                                                (flag_rect.x - camera_x+44, flag_rect.y - 20),
                                                (flag_rect.x - camera_x+4, flag_rect.y   )])
        # Coins
        for c in coins:
            c.draw(window, camera_x)
        # Enemies
        for en in enemies:
            en.draw(window, camera_x)
        # Player
        player.draw(window, camera_x)

        # HUD
        font = pygame.font.SysFont(None, 30)
        window.blit(font.render(f"Score: {score}", True, (0,0,0)), (12,12))

        pygame.display.update()

# ------------------ Main ------------------
def main():
    main_menu()
    level = 1
    while True:
        level_intro(level)
        result, score = run_level(level)
        if result == "dead":
            action = game_over_screen(score)
            if action == "retry":
                continue
            else:
                break
        elif result == "complete":
            level_complete_screen(level, score)
            level += 1  # in this starter, same layout repeats; you can expand build_level()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
