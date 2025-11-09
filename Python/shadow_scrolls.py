import pygame, sys, os, json, math, random
pygame.init()

# ----------------- Window / Global -----------------
WIDTH, HEIGHT = 960, 540
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Ten Ninja Scrolls")
clock = pygame.time.Clock()
FPS = 60

# Physics
GRAVITY = 0.6
MOVE_SPEED = 5
JUMP_POWER = -12
DOUBLE_JUMP_POWER = -11
DASH_SPEED = 12
TILE = 48

# Colors
BLACK=(0,0,0); WHITE=(255,255,255)
INK=(25,25,25); GOLD=(255,215,0); RED=(220,70,70)

# Save file
SAVE_FILE = "ninja_progress.json"

# ----------------- Assets -----------------
def load_sheet(path, fw, fh):
    img = pygame.image.load(path).convert_alpha()
    cols = img.get_width()//fw
    return [img.subsurface(pygame.Rect(i*fw,0,fw,fh)) for i in range(cols)]

def safe_sheet(path, fw, fh):
    try: return load_sheet(path, fw, fh)
    except: return []

def safe_img(path):
    try: return pygame.image.load(path).convert_alpha()
    except: return None

IDLE = safe_sheet("player_idle.png",48,48)
RUN  = safe_sheet("player_run.png",48,48)
JUMP = safe_sheet("player_jump.png",48,48)
DJMP = safe_sheet("player_doublejump.png",48,48)

EWALK = safe_sheet("enemy_walk.png",48,48)
ESTOMP = safe_sheet("enemy_stomp.png",48,48)

COIN = safe_sheet("coin.png",32,32)

BG_SKY = safe_img("bg_sky.png")
BG_MTN = safe_img("bg_mountains.png")
BG_TRE = safe_img("bg_trees.png")
BG_GRA = safe_img("bg_grass.png")

# Music
try:
    pygame.mixer.music.load("bg_music.wav")
    pygame.mixer.music.set_volume(0.5)
except:
    pass

# SFX (fallback beeps using pygame if you don’t have files)
# eat_sfx = pygame.mixer.Sound(None)
# hit_sfx = pygame.mixer.Sound(None)

# ----------------- Parallax -----------------
class Parallax:
    def __init__(self):
        self.layers = [(BG_SKY,0.1),(BG_MTN,0.3),(BG_TRE,0.6),(BG_GRA,0.9)]
    def draw(self, surf, camx):
        surf.fill((120,180,255))
        for img, speed in self.layers:
            if not img: continue
            w = img.get_width()
            x = - (camx * speed) % w
            surf.blit(img, (x-w,0)); surf.blit(img, (x,0)); surf.blit(img, (x+w,0))

# ----------------- Level Geometry -----------------
class Platform:
    def __init__(self, rect): self.rect = pygame.Rect(rect)
    def draw(self, surf, camx):
        pygame.draw.rect(surf,(60,170,70),(self.rect.x-camx,self.rect.y,self.rect.w,self.rect.h))

# ----------------- Collectibles -----------------
class Coin:
    def __init__(self, x,y):
        self.rect = pygame.Rect(x,y,24,24)
        self.t=0
    def update(self): self.t+=1
    def draw(self, surf, camx):
        if COIN:
            frame = COIN[(self.t//6)%len(COIN)]
            surf.blit(frame,(self.rect.x-camx-4,self.rect.y-4))
        else:
            pygame.draw.circle(surf,GOLD,(self.rect.x-camx+12,self.rect.y+12),12)
    def collect(self, player): return self.rect.colliderect(player.rect)

# ----------------- Enemies -----------------
class Enemy:
    def __init__(self,x,y,lbound,rbound):
        self.rect=pygame.Rect(x,y,40,44)
        self.vx=2
        self.l=lbound; self.r=rbound
        self.stomped=False; self.dead_time=0
        self.hp=10
    def update(self):
        if self.stomped:
            self.dead_time+=1
            return
        self.rect.x+=self.vx
        if self.rect.x<self.l or self.rect.x>self.r: self.vx*=-1
    def draw(self,surf,camx):
        if self.stomped and ESTOMP:
            surf.blit(ESTOMP[0],(self.rect.x-camx-4,self.rect.y-4))
        elif EWALK:
            frame = EWALK[(pygame.time.get_ticks()//120)%len(EWALK)]
            img = pygame.transform.flip(frame, self.vx<0, False)
            surf.blit(img,(self.rect.x-camx-4,self.rect.y-4))
        else:
            pygame.draw.rect(surf,RED,(self.rect.x-camx,self.rect.y,self.rect.w,self.rect.h))

# ----------------- Boss (Template) -----------------
class Boss:
    def __init__(self, x,y, arena_left, arena_right, name="Boss"):
        self.rect=pygame.Rect(x,y,64,64)
        self.vx=3; self.dir=1
        self.left=arena_left; self.right=arena_right
        self.hp=10
        self.name=name
        self.phase=1
        self.cool=0
    def update(self, player):
        if self.hp<=0: return
        if self.cool>0: self.cool-=1
        # simple patrol with occasional leaps towards player
        self.rect.x += self.vx*self.dir
        if self.rect.x<self.left or self.rect.x>self.right: self.dir*=-1
        # jump strike
        if self.cool==0 and abs(player.rect.centerx-self.rect.centerx)<200:
            self.cool=90
            self.dir = 1 if player.rect.centerx>self.rect.centerx else -1
            # little hop (fake)
    def hit(self, dmg=1):
        if self.hp>0: self.hp-=dmg
    def draw(self,surf,camx):
        # draw body
        pygame.draw.rect(surf,(60,60,80),(self.rect.x-camx,self.rect.y,self.rect.w,self.rect.h),0,8)
        # face slash lines
        pygame.draw.line(surf,(200,0,0),(self.rect.x-camx+10,self.rect.y+20),(self.rect.x-camx+54,self.rect.y+24),3)
        # HP bar
        bar_w=300
        pygame.draw.rect(surf,(40,40,40),(WIDTH//2-bar_w//2,20,bar_w,16),2)
        hp_w=int(bar_w*max(self.hp,0)/10)
        pygame.draw.rect(surf,(220,70,70),(WIDTH//2-bar_w//2,20,hp_w,16))
        font=pygame.font.SysFont(None,28)
        surf.blit(font.render(self.name,True,WHITE),(WIDTH//2-60,42))

# ----------------- Player -----------------
class Player:
    def __init__(self,x,y, abilities):
        self.rect=pygame.Rect(x,y,40,46)
        self.vx=0; self.vy=0
        self.facing_left=False
        self.on_ground=False
        self.can_double=True
        self.abilities=abilities
        self.dash_cd=0
        self.slowmo=False
        self.focus=100  # for slow-mo
        self.shadow_timer=0 # shadow form visual
        self.anim_t=0
        self.invul=0
        self.slide=False

        self.projectiles=[]  # shurikens: list of rect + vx

    def handle_input(self, keys):
        self.vx=0
        if keys[pygame.K_LEFT]:
            self.vx=-MOVE_SPEED; self.facing_left=True
        if keys[pygame.K_RIGHT]:
            self.vx= MOVE_SPEED; self.facing_left=False

        # Jump / Double jump
        if keys[pygame.K_UP]:
            if self.on_ground:
                self.vy=JUMP_POWER; self.on_ground=False; self.can_double=True
            elif self.abilities["double_jump"] and self.can_double:
                self.vy=DOUBLE_JUMP_POWER; self.can_double=False

        # Dash
        if self.abilities["dash"] and keys[pygame.K_LSHIFT] and self.dash_cd==0:
            self.vx = (-DASH_SPEED if self.facing_left else DASH_SPEED)
            self.dash_cd = 30

        # Slide (hold down while moving)
        self.slide = False
        if self.abilities["slide"] and keys[pygame.K_DOWN] and (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]):
            self.slide=True
            self.vx *= 1.2

        # Shuriken
        if self.abilities["shuriken"] and keys[pygame.K_x]:
            if len(self.projectiles)<3:
                r=pygame.Rect(self.rect.centerx, self.rect.centery, 10, 4)
                vx=9 * (-1 if self.facing_left else 1)
                self.projectiles.append([r,vx])

        # Shadow clone (decoy)
        # press C to drop a decoy that distracts enemies (cosmetic)
        # (we just spawn a fading silhouette)
        if self.abilities["clone"] and keys[pygame.K_c]:
            self.shadow_timer=15

        # Slow-mo toggle
        if self.abilities["slowmo"] and keys[pygame.K_f]:
            if self.focus>0:
                self.slowmo=True

    def physics(self, platforms):
        # Horizontal
        self.rect.x += int(self.vx)
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vx>0: self.rect.right=p.rect.left
                elif self.vx<0: self.rect.left=p.rect.right

        # Gravity + vertical
        self.vy += (GRAVITY*0.6 if self.abilities["slowfall"] and not self.on_ground else GRAVITY)
        self.rect.y += int(self.vy)
        self.on_ground=False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy>0:
                    self.rect.bottom=p.rect.top; self.vy=0; self.on_ground=True; self.can_double=True
                elif self.vy<0:
                    self.rect.top=p.rect.bottom; self.vy=0

        # cooldowns
        if self.dash_cd>0: self.dash_cd-=1
        if self.invul>0: self.invul-=1

        # projectiles
        for pr in self.projectiles[:]:
            pr[0].x += pr[1]
            if pr[0].x<-2000 or pr[0].x>5000: self.projectiles.remove(pr)

        # slow-mo drain
        if self.slowmo:
            self.focus -= 0.5
            if self.focus<=0: self.slowmo=False
        else:
            self.focus = min(100, self.focus+0.2)

    def stomp_enemy(self, enemy):
        feet=pygame.Rect(self.rect.x+6,self.rect.bottom-6,self.rect.w-12,8)
        head=pygame.Rect(enemy.rect.x,enemy.rect.y,enemy.rect.w,10)
        return self.vy>0 and feet.colliderect(head)

    def ground_slam(self, enemies):
        # Z to slam: small AoE beneath player
        # (Handled in level loop on keypress)
        pass

    def wall_jump(self, platforms, keys):
        if not self.abilities["wall_jump"]: return
        touching_left=False; touching_right=False
        self.rect.x -= 1
        for p in platforms:
            if self.rect.colliderect(p.rect): touching_left=True; break
        self.rect.x += 2
        for p in platforms:
            if self.rect.colliderect(p.rect): touching_right=True; break
        self.rect.x -=1

        if (touching_left or touching_right) and keys[pygame.K_UP]:
            self.vy = JUMP_POWER
            self.vx = (MOVE_SPEED if touching_left else -MOVE_SPEED)
            self.on_ground=False
            self.can_double=True

    def draw(self, surf, camx):
        self.anim_t += 1
        # shadow form tint
        glow = self.abilities["shadow_form"]

        # choose frame
        img=None
        if not self.on_ground:
            if not self.can_double and DJMP: img=DJMP[0]
            elif JUMP: img=JUMP[0]
        else:
            if abs(self.vx)>0 and RUN: img = RUN[(self.anim_t//6)%len(RUN)]
            elif IDLE: img = IDLE[(self.anim_t//10)%len(IDLE)]

        if img:
            img = pygame.transform.flip(img, self.facing_left, False)
            if glow:
                # simple glow: draw a tinted underlay
                glow_surf = img.copy(); arr=pygame.PixelArray(glow_surf); arr.replace(arr.make_surface().map_rgb((0,0,0)), (0,0,0))
                del arr
            surf.blit(img,(self.rect.x-camx-4,self.rect.y-2))
        else:
            pygame.draw.rect(surf,(80,80,255),(self.rect.x-camx,self.rect.y,self.rect.w,self.rect.h))

        # clone silhouette
        if self.shadow_timer>0:
            self.shadow_timer-=1
            s=pygame.Surface((self.rect.w,self.rect.h),pygame.SRCALPHA)
            s.fill((50,50,80,80))
            surf.blit(s,(self.rect.x-camx,self.rect.y))

        # projectiles
        for pr in self.projectiles:
            pygame.draw.rect(surf,(200,200,200),(pr[0].x - camx, pr[0].y, pr[0].w, pr[0].h))

# ----------------- Levels -----------------
def build_level(world, sublevel):
    """
    world: 1..10, sublevel: 1,2 or 'boss'
    We keep geometry lightweight and fun. You can expand later.
    """
    platforms=[
        Platform((-200,480,2600,60)),
        Platform(( 200,420,180,16)),
        Platform(( 500,360,180,16)),
        Platform(( 820,320,200,16)),
        Platform((1120,360,200,16)),
        Platform((1420,300,200,16)),
        Platform((1720,420,220,16)),
    ]
    coins=[Coin(230,380),Coin(520,320),Coin(850,280),Coin(1150,320),Coin(1450,260),Coin(1750,380)]
    enemies=[Enemy(560,436,520,780), Enemy(1180,436,1120,1400), Enemy(1520,376,1480,1750)]

    # slight variations per world for flavor
    for p in platforms[1:]:
        p.rect.y -= (world-1)*4
    for e in enemies:
        e.vx += (world-1)*0.1

    # Boss arena
    boss=None
    flag_rect=None
    if sublevel=="boss":
        platforms=[Platform((-200,480,2400,60)), Platform((700,420,500,16)), Platform((1300,360,500,16))]
        enemies=[]
        boss_names=["Wind Assassin","Moonblade Ninja","Fire Oni","Phantom Shinobi","Kappa General",
                    "Ronin Shogun","Raijin Monk","Stone Titan","Timekeeper Samurai","Shadow Grandmaster"]
        boss=Boss(1100,416,800,1600,name=boss_names[world-1])
    else:
        # Level end flag
        flag_rect=pygame.Rect(2100,420,20,60)

    return platforms, coins, enemies, boss, flag_rect

# ----------------- HUD -----------------
def draw_hud(surf, score, abilities, focus):
    font=pygame.font.SysFont(None,28)
    surf.blit(font.render(f"Score: {score}",True,BLACK),(12,12))
    # abilities icons (text)
    xs=12; ys=44
    show=[]
    for key, label in [("double_jump","DJ"),("wall_jump","WJ"),("dash","DS"),("shuriken","SH"),("slowfall","SF"),
                       ("clone","CL"),("slam","SL"),("slide","SLD"),("slowmo","TM"),("shadow_form","SFm")]:
        if abilities[key]: show.append(label)
    if show:
        surf.blit(font.render("Abilities: "+" ".join(show),True,(20,20,20)),(xs,ys))
    # Focus bar (for time slow)
    pygame.draw.rect(surf,(30,30,30),(WIDTH-170,14,156,14),2)
    pygame.draw.rect(surf,(80,180,255),(WIDTH-168,16,int( (focus/100)*152 ),10))

# ----------------- Pause -----------------
def pause_menu():
    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: return
        s=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); s.fill((0,0,0,120))
        window.blit(s,(0,0))
        font=pygame.font.SysFont(None,54)
        window.blit(font.render("PAUSED",True,WHITE),(WIDTH//2-100,HEIGHT//2-20))
        pygame.display.update(); clock.tick(30)

# ----------------- Level Loop -----------------
def play_level(world, sublevel, abilities, score):
    par=Parallax()
    platforms, coins, enemies, boss, flag_rect = build_level(world, sublevel)
    player=Player(100,380,abilities.copy())
    camera_x=0
    slow_factor=1.0

    while True:
        dt=clock.tick(FPS)
        # slow-mo
        slow_factor = 0.5 if player.slowmo else 1.0

        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_ESCAPE: pause_menu()

        keys=pygame.key.get_pressed()
        player.handle_input(keys)
        player.wall_jump(platforms, keys)

        # ground slam
        if abilities["slam"] and keys[pygame.K_z] and not player.on_ground and player.vy>0:
            # knock out nearby enemies below
            slam_rect = pygame.Rect(player.rect.centerx-40, player.rect.bottom, 80, 40)
            for en in enemies:
                if slam_rect.colliderect(en.rect): en.stomped=True
            # little bounce
            player.vy = -6

        # physics with slow-mo consideration (simplified: we don't alter actual physics; we alter dt feel)
        player.physics(platforms)

        # coins
        for c in coins[:]:
            c.update()
            if c.collect(player):
                coins.remove(c); score+=1

        # enemies
        for en in enemies[:]:
            en.update()
            # shuriken hit
            for pr in player.projectiles[:]:
                if en.rect.colliderect(pr[0]):
                    en.stomped=True; player.projectiles.remove(pr)
            # stomp
            if not en.stomped and player.stomp_enemy(en):
                en.stomped=True; player.vy = JUMP_POWER*0.6; score+=5
            # collision kill
            if not en.stomped and player.rect.colliderect(en.rect) and player.invul==0:
                return ("dead", score)
            # cleanup
            if en.stomped and en.dead_time>30: enemies.remove(en)

        # boss
        if boss:
            boss.update(player)
            # shuriken hits boss
            for pr in player.projectiles[:]:
                if boss.rect.colliderect(pr[0]) and boss.hp>0:
                    boss.hit(1); player.projectiles.remove(pr)
            # stomp boss (deal 1 damage)
            feet = pygame.Rect(player.rect.x+6, player.rect.bottom-6, player.rect.w-12, 8)
            if boss.hp > 0 and feet.colliderect(boss.rect) and player.vy > 0:
               boss.hit(1)
               player.vy = JUMP_POWER * 0.6

            # boss touch hurts
            if boss.hp>0 and player.rect.colliderect(boss.rect) and player.invul==0:
                return ("dead", score)
            # boss defeated?
            if boss.hp <= 0:
                # boss death animation goes here later
                return ("boss_down", score)


        # finish level (flag)
        if flag_rect and player.rect.colliderect(flag_rect):
            return ("win", score)

        # camera
        camera_x = max(0, int(player.rect.centerx - WIDTH*0.5))

        # draw
        par.draw(window,camera_x)
        for p in platforms: p.draw(window,camera_x)
        if flag_rect:
            pygame.draw.rect(window,WHITE,(flag_rect.x-camera_x,flag_rect.y-40,4,100))
            pygame.draw.polygon(window,RED,[(flag_rect.x-camera_x+4,flag_rect.y-40),
                                            (flag_rect.x-camera_x+44,flag_rect.y-20),
                                            (flag_rect.x-camera_x+4,flag_rect.y)])
        for c in coins: c.draw(window,camera_x)
        for en in enemies: en.draw(window,camera_x)
        if boss: boss.draw(window,camera_x)
        player.draw(window,camera_x)
        draw_hud(window, score, abilities, player.focus)
        pygame.display.update()

# ----------------- Story / Progress -----------------
DEFAULT_ABILITIES = {
    "double_jump": True,   # tutorialized early
    "wall_jump":   False,
    "dash":        False,
    "clone":       False,
    "slowfall":    False,
    "shuriken":    False,
    "slam":        False,
    "slide":       False,
    "slowmo":      False,
    "shadow_form": False,
}

WORLD_NAMES = [
    "Bamboo Forest","Night Temple","Volcanic Caverns","Misty Graveyard","Flooded Ruins",
    "Floating Dojo","Thunder Peaks","Ancient Caves","Crumbling Temple","Shadow Realm"
]

UNLOCK_ORDER = [
    "double_jump",   # W1 (already active; beating boss formalizes)
    "wall_jump",     # W2
    "dash",          # W3
    "clone",         # W4
    "slowfall",      # W5
    "shuriken",      # W6
    "slam",          # W7
    "slide",         # W8
    "slowmo",        # W9
    "shadow_form"    # W10
]

def load_progress():
    if not os.path.exists(SAVE_FILE):
        return {"world_unlocked":1, "scrolls":0, "abilities":DEFAULT_ABILITIES.copy(), "coins":0}
    with open(SAVE_FILE,"r") as f:
        data=json.load(f)
    # ensure keys
    for k in DEFAULT_ABILITIES:
        if k not in data["abilities"]: data["abilities"][k]=DEFAULT_ABILITIES[k]
    return data

def save_progress(data):
    with open(SAVE_FILE,"w") as f: json.dump(data,f,indent=2)

# ----------------- Map (Japanese Scroll Style) -----------------
def draw_parchment_bg(surf):
    # simple parchment gradient + edges (no external asset)
    surf.fill((240,228,200))
    edge = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    pygame.draw.rect(edge,(0,0,0,40),(0,0,WIDTH,HEIGHT),40)
    surf.blit(edge,(0,0))
    # bamboo rods
    pygame.draw.rect(surf,(180,150,90),(0,8,WIDTH,12))
    pygame.draw.rect(surf,(180,150,90),(0,HEIGHT-20,WIDTH,12))

def world_map_screen(progress):
    # music
    try:
        if not pygame.mixer.music.get_busy(): pygame.mixer.music.play(-1)
    except: pass

    index=0
    running=True
    while running:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_LEFT: index=max(0,index-1)
                if e.key==pygame.K_RIGHT: index=min(9,index+1)
                if e.key==pygame.K_RETURN:
                    if index+1 <= progress["world_unlocked"]:
                        return index+1   # selected world to play
                if e.key==pygame.K_ESCAPE:
                    return None

        draw_parchment_bg(window)
        # title
        title=pygame.font.SysFont(None,52).render("THE TEN NINJA SCROLLS",True,INK)
        window.blit(title,(WIDTH//2 - title.get_width()//2, 40))

        # nodes
        start_x=80; spacing=(WIDTH-160)//9
        for i in range(10):
            x = start_x + spacing*i
            y = HEIGHT//2 + int(50*math.sin(i))
            unlocked = (i+1) <= progress["world_unlocked"]
            cleared  = (i+1) < progress["world_unlocked"]
            color = (40,40,40) if unlocked else (120,120,120)
            pygame.draw.circle(window,color,(x,y),16)
            # label
            lab=pygame.font.SysFont(None,24).render(str(i+1),True,WHITE)
            window.blit(lab,(x-8,y-10))
            # completed red stamp
            if cleared:
                pygame.draw.circle(window,(180,30,30),(x,y),20,3)

        # selector brush mark
        sel_x = start_x + spacing*index
        sel_y = HEIGHT//2 + int(50*math.sin(index))
        pygame.draw.circle(window,(0,0,0),(sel_x,sel_y),22,3)

        # world info
        name_txt = pygame.font.SysFont(None,36).render(WORLD_NAMES[index],True,(40,40,40))
        window.blit(name_txt,(WIDTH//2 - name_txt.get_width()//2, HEIGHT-120))

        # lock text
        if index+1 > progress["world_unlocked"]:
            lock_txt = pygame.font.SysFont(None,26).render("Sealed: recover earlier scrolls to enter",True,(80,20,20))
            window.blit(lock_txt,(WIDTH//2 - lock_txt.get_width()//2, HEIGHT-80))
        else:
            hint_txt = pygame.font.SysFont(None,26).render("Press Enter to play",True,(20,60,20))
            window.blit(hint_txt,(WIDTH//2 - hint_txt.get_width()//2, HEIGHT-80))

        pygame.display.update()
        clock.tick(60)

# ----------------- Cutscenes -----------------
def scroll_unlocked_cutscene(world_idx, ability_key):
    t=0
    msg1=f"Scroll {world_idx} recovered!"
    pretty={
        "double_jump":"Double Jump",
        "wall_jump":"Wall Jump",
        "dash":"Dash",
        "clone":"Shadow Clone",
        "slowfall":"Slow Fall",
        "shuriken":"Shuriken",
        "slam":"Ground Slam",
        "slide":"Slide",
        "slowmo":"Time Slow",
        "shadow_form":"Shadow Form",
    }
    msg2=f"New Ability: {pretty.get(ability_key, ability_key)}"
    while t<180:
        window.fill((10,10,10))
        font1=pygame.font.SysFont(None,56)
        font2=pygame.font.SysFont(None,36)
        window.blit(font1.render(msg1,True,WHITE),(WIDTH//2-220,HEIGHT//2-40))
        window.blit(font2.render(msg2,True,(200,220,255)),(WIDTH//2-220,HEIGHT//2+10))
        pygame.display.update(); clock.tick(60); t+=1

# ----------------- Main Flow -----------------
def main_menu():
    try:
        if not pygame.mixer.music.get_busy(): pygame.mixer.music.play(-1)
    except: pass

    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_RETURN: return
        window.fill((15,15,25))
        f1=pygame.font.SysFont(None,64)
        f2=pygame.font.SysFont(None,30)
        window.blit(f1.render("THE TEN NINJA SCROLLS",True,WHITE),(WIDTH//2-350,160))
        window.blit(f2.render("Press Enter",True,(200,220,255)),(WIDTH//2-70,260))
        window.blit(f2.render("Arrow keys to move; ↑ jump; Shift=dash; X=shuriken; F=time slow",True,(180,180,180)),(WIDTH//2-360,320))
        pygame.display.update(); clock.tick(60)

def run_world(world_idx, progress):
    """
    Plays Level 1, Level 2, then Boss for the given world index (1..10).
    Returns updated progress/state.
    """
    # local abilities copy
    abilities = progress["abilities"]

    # Level 1
    result, score = play_level(world_idx, 1, abilities, progress["coins"])
    if result=="dead": return progress  # retry from map
    progress["coins"]=score

    # Level 2
    result, score = play_level(world_idx, 2, abilities, progress["coins"])
    if result=="dead": return progress
    progress["coins"]=score

    # Boss
    result, score = play_level(world_idx, "boss", abilities, progress["coins"])
    if result!="boss_down": return progress
    progress["coins"]=score

    # Unlock next world & grant ability
    progress["scrolls"] = max(progress["scrolls"], world_idx)
    if world_idx < 10:
        progress["world_unlocked"] = max(progress["world_unlocked"], world_idx+1)

    ability_key = UNLOCK_ORDER[world_idx-1]
    progress["abilities"][ability_key]=True
    scroll_unlocked_cutscene(world_idx, ability_key)
    save_progress(progress)
    return progress

def main():
    progress = load_progress()
    main_menu()

    while True:
        # World Map
        w = world_map_screen(progress)
        if w is None:
            pygame.quit(); sys.exit()

        # Play selected world if unlocked (enforced in map)
        progress = run_world(w, progress)

if __name__=="__main__":
    main()
