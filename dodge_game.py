import pygame
import random
import sys
import math
from dataclasses import dataclass
from pathlib import Path

pygame.init()

# -------------------------
# Screen / Basic
# -------------------------
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dodge Game")

clock = pygame.time.Clock()
FPS = 60

BLACK = (0, 0, 0)
WHITE = (245, 245, 245)

# Style: obstacle=red, coin=gold, player=green
RED = (235, 70, 70)
GOLD_OUTER = (220, 175, 55)
GOLD_INNER = (255, 215, 80)
GOLD_RIM = (255, 235, 150)
GREEN = (70, 220, 120)
BLUE = (90, 170, 255)

font = pygame.font.SysFont(None, 34)
big_font = pygame.font.SysFont(None, 84)

SAVE_PATH = Path("best_time.txt")


# -------------------------
# Best record save/load
# -------------------------
def load_best():
    try:
        return float(SAVE_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        return 0.0


def save_best(best: float):
    try:
        SAVE_PATH.write_text(f"{best:.1f}", encoding="utf-8")
    except Exception:
        pass


best_time = load_best()


# -------------------------
# Utils
# -------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_text_center(text, y, color=WHITE, use_big=False):
    f = big_font if use_big else font
    surf = f.render(text, True, color)
    screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))


def draw_bar(x, y, w, h, value01, fg_color, bg_color=(35, 35, 35)):
    pygame.draw.rect(screen, bg_color, (x, y, w, h))
    fill = int(w * clamp(value01, 0.0, 1.0))
    pygame.draw.rect(screen, fg_color, (x, y, fill, h))
    pygame.draw.rect(screen, (70, 70, 70), (x, y, w, h), 2)


# -------------------------
# Coin drawing (coin-like, not just a circle)
# -------------------------
def draw_coin(surface, rect: pygame.Rect):
    cx, cy = rect.center
    r = min(rect.width, rect.height) // 2

    # Outer rim
    pygame.draw.circle(surface, GOLD_OUTER, (cx, cy), r)
    # Inner face
    pygame.draw.circle(surface, GOLD_INNER, (cx, cy), int(r * 0.82))
    # Ring highlight
    pygame.draw.circle(surface, GOLD_RIM, (cx, cy), int(r * 0.70), 2)

    # Specular highlight
    hl_r = max(2, int(r * 0.22))
    pygame.draw.circle(surface, (255, 245, 210), (cx - int(r * 0.25), cy - int(r * 0.25)), hl_r)

    # Side groove line
    line_color = (235, 195, 85)
    pygame.draw.line(
        surface,
        line_color,
        (cx - int(r * 0.18), cy - int(r * 0.35)),
        (cx - int(r * 0.18), cy + int(r * 0.35)),
        2,
    )


# -------------------------
# Particles (subtle)
# -------------------------
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    age: float
    radius: float
    color: tuple

    def update(self, dt):
        self.age += dt
        self.vy += 420 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def alive(self):
        return self.age < self.life

    def draw(self, surf):
        t = clamp(self.age / self.life, 0.0, 1.0)
        r = max(1, int(self.radius * (1.0 - t)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


def emit_particles(particles, x, y, color, count=12, power=200):
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(power * 0.45, power)
        vx = math.cos(ang) * spd
        vy = math.sin(ang) * spd - random.uniform(0, power * 0.2)
        life = random.uniform(0.20, 0.42)
        radius = random.uniform(2.2, 5.8)
        particles.append(Particle(x, y, vx, vy, life, 0.0, radius, color))


# -------------------------
# Game objects
# -------------------------
@dataclass
class Obstacle:
    rect: pygame.Rect
    speed: float

    def update(self, dt):
        self.rect.y += int(self.speed * dt)

    def draw(self, surf):
        pygame.draw.rect(surf, RED, self.rect, border_radius=8)


@dataclass
class Coin:
    rect: pygame.Rect
    speed: float

    def update(self, dt):
        self.rect.y += int(self.speed * dt)

    def draw(self, surf):
        draw_coin(surf, self.rect)


def spawn_obstacle(level: int) -> Obstacle:
    w = random.randint(36, 88)
    h = random.randint(36, 88)
    x = random.randint(0, WIDTH - w)
    y = -h
    speed = 220 + level * 18 + random.randint(-20, 40)
    return Obstacle(pygame.Rect(x, y, w, h), speed)


def spawn_coin(level: int) -> Coin:
    size = random.randint(22, 30)
    x = random.randint(0, WIDTH - size)
    y = -size
    speed = 240 + level * 10 + random.randint(-10, 25)
    return Coin(pygame.Rect(x, y, size, size), speed)


# -------------------------
# Reset
# -------------------------
def reset_game():
    player = pygame.Rect(WIDTH // 2 - 25, HEIGHT - 95, 50, 50)

    # Move / Dash
    player_speed = 280.0
    dash_speed = 680.0
    dash_duration = 0.12
    dash_cooldown = 0.55
    dash_until = 0.0
    dash_cd_until = 0.0

    hp = 3
    invincible_until = 0.0

    score = 0
    combo = 0
    combo_timer = 0.0
    combo_keep = 2.0

    t = 0.0

    obstacles = []
    coins = []
    particles = []

    obs_timer = 0.0
    coin_timer = 0.0

    paused = False
    game_over = False

    return {
        "player": player,
        "player_speed": player_speed,
        "dash_speed": dash_speed,
        "dash_duration": dash_duration,
        "dash_cooldown": dash_cooldown,
        "dash_until": dash_until,
        "dash_cd_until": dash_cd_until,
        "hp": hp,
        "invincible_until": invincible_until,
        "score": score,
        "combo": combo,
        "combo_timer": combo_timer,
        "combo_keep": combo_keep,
        "t": t,
        "obstacles": obstacles,
        "coins": coins,
        "particles": particles,
        "obs_timer": obs_timer,
        "coin_timer": coin_timer,
        "paused": paused,
        "game_over": game_over,
    }


# -------------------------
# Main loop
# -------------------------
state = "MENU"  # MENU / PLAY
game = reset_game()

p_was = False
shift_was = False

while True:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        pygame.quit()
        sys.exit()

    # ---------------- MENU ----------------
    if state == "MENU":
        if keys[pygame.K_SPACE]:
            game = reset_game()
            state = "PLAY"

        screen.fill(BLACK)
        draw_text_center("DODGE GAME", 160, use_big=True)
        draw_text_center("Press SPACE to Start", 290, color=GOLD_INNER)
        draw_text_center("Move: LEFT/RIGHT   Dash: SHIFT   Pause: P", 340)
        draw_text_center("Coins = Score + Combo | Red blocks = Damage", 390)
        draw_text_center(f"Best Time: {best_time:.1f}s", 460, color=GREEN)
        pygame.display.flip()
        continue

    # ---------------- PLAY ----------------
    # Pause toggle
    p_down = keys[pygame.K_p]
    if p_down and not p_was and (not game["game_over"]):
        game["paused"] = not game["paused"]
    p_was = p_down

    # Game over inputs
    if game["game_over"]:
        if keys[pygame.K_r]:
            game = reset_game()
        if keys[pygame.K_m]:
            state = "MENU"

    # Time advance
    if (not game["paused"]) and (not game["game_over"]):
        game["t"] += dt

    level = 1 + int(game["t"] // 10)
    now_t = game["t"]

    # Dash (one-press)
    shift_down = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
    can_dash = (now_t >= game["dash_cd_until"]) and (now_t >= game["dash_until"]) and (not game["paused"]) and (not game["game_over"])

    if shift_down and not shift_was and can_dash:
        game["dash_until"] = now_t + game["dash_duration"]
        game["dash_cd_until"] = now_t + game["dash_cooldown"]
        emit_particles(game["particles"], game["player"].centerx, game["player"].centery, BLUE, count=10, power=170)

    shift_was = shift_down

    dash_ready = 1.0
    if now_t < game["dash_cd_until"]:
        remain = game["dash_cd_until"] - now_t
        dash_ready = 1.0 - clamp(remain / game["dash_cooldown"], 0.0, 1.0)

    # Update
    if (not game["paused"]) and (not game["game_over"]):
        move_dir = 0
        if keys[pygame.K_LEFT]:
            move_dir -= 1
        if keys[pygame.K_RIGHT]:
            move_dir += 1

        in_dash = now_t < game["dash_until"]
        speed = game["dash_speed"] if in_dash else game["player_speed"]

        game["player"].x += int(move_dir * speed * dt)
        game["player"].x = clamp(game["player"].x, 0, WIDTH - game["player"].width)

        # Spawn
        game["obs_timer"] += dt
        obs_interval = max(0.20, 0.58 - level * 0.03)
        if game["obs_timer"] >= obs_interval:
            game["obs_timer"] = 0.0
            game["obstacles"].append(spawn_obstacle(level))

        game["coin_timer"] += dt
        coin_interval = max(0.45, 0.95 - level * 0.02)
        if game["coin_timer"] >= coin_interval:
            game["coin_timer"] = 0.0
            game["coins"].append(spawn_coin(level))

        # Move objects
        for o in game["obstacles"]:
            o.update(dt)
        for c in game["coins"]:
            c.update(dt)

        # Remove off-screen
        game["obstacles"] = [o for o in game["obstacles"] if o.rect.y < HEIGHT + 160]
        game["coins"] = [c for c in game["coins"] if c.rect.y < HEIGHT + 120]

        # Combo decay
        if game["combo"] > 0:
            game["combo_timer"] -= dt
            if game["combo_timer"] <= 0:
                game["combo"] = max(0, game["combo"] - 1)
                game["combo_timer"] = game["combo_keep"] * 0.6 if game["combo"] > 0 else 0.0

        # Coin collision
        new_coins = []
        for c in game["coins"]:
            if game["player"].colliderect(c.rect):
                game["combo"] += 1
                game["combo_timer"] = game["combo_keep"]
                mult = 1 + min(game["combo"] // 5, 6)
                game["score"] += 10 * mult
                emit_particles(game["particles"], c.rect.centerx, c.rect.centery, GOLD_INNER, count=12, power=200)
            else:
                new_coins.append(c)
        game["coins"] = new_coins

        # Obstacle collision (invincibility)
        invincible = game["t"] < game["invincible_until"]
        if not invincible:
            for o in game["obstacles"]:
                if game["player"].colliderect(o.rect):
                    game["hp"] -= 1
                    game["invincible_until"] = game["t"] + 0.8
                    emit_particles(game["particles"], game["player"].centerx, game["player"].centery, RED, count=16, power=240)
                    game["combo"] = max(0, game["combo"] - 2)
                    game["combo_timer"] = game["combo_keep"] * 0.5 if game["combo"] > 0 else 0.0
                    break

        if game["hp"] <= 0:
            game["game_over"] = True

        # Best time update
        if (not game["game_over"]) and (game["t"] > best_time):
            best_time = game["t"]
            save_best(best_time)

    # Particle update (slower when paused)
    pdt = dt * (0.18 if game["paused"] else 1.0)
    for p in game["particles"]:
        p.update(pdt)
    game["particles"] = [p for p in game["particles"] if p.alive()]

    # Render
    screen.fill(BLACK)

    for o in game["obstacles"]:
        o.draw(screen)
    for c in game["coins"]:
        c.draw(screen)
    for p in game["particles"]:
        p.draw(screen)

    # Player (blink when invincible)
    invincible = game["t"] < game["invincible_until"]
    if (not invincible) or (int(game["t"] * 12) % 2 == 0):
        pygame.draw.rect(screen, GREEN, game["player"], border_radius=10)

    # UI
    ui_time = font.render(f"Time: {game['t']:.1f}s", True, WHITE)
    ui_level = font.render(f"Level: {level}", True, WHITE)
    ui_hp = font.render(f"HP: {game['hp']}", True, WHITE)
    ui_score = font.render(f"Score: {game['score']}", True, WHITE)
    ui_combo = font.render(f"Combo: {game['combo']}", True, GOLD_INNER if game["combo"] > 0 else WHITE)
    ui_best = font.render(f"Best: {best_time:.1f}s", True, GREEN)

    screen.blit(ui_time, (20, 16))
    screen.blit(ui_level, (20, 48))
    screen.blit(ui_hp, (20, 80))
    screen.blit(ui_score, (20, 112))
    screen.blit(ui_combo, (20, 144))
    screen.blit(ui_best, (20, 176))

    dash_label = font.render("Dash", True, BLUE)
    screen.blit(dash_label, (WIDTH - 170, 16))
    draw_bar(WIDTH - 170, 46, 140, 18, dash_ready, BLUE)

    tip = font.render("SHIFT: Dash | P: Pause | R: Restart | M: Menu | ESC: Quit", True, (170, 170, 170))
    screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 36))

    if game["paused"] and not game["game_over"]:
        draw_text_center("PAUSED", HEIGHT // 2 - 90, use_big=True)
        draw_text_center("Press P to Resume", HEIGHT // 2 + 10, color=GOLD_INNER)

    if game["game_over"]:
        draw_text_center("GAME OVER", HEIGHT // 2 - 120, use_big=True)
        draw_text_center("R: Restart   M: Menu   ESC: Quit", HEIGHT // 2 - 20, color=GOLD_INNER)

    pygame.display.flip()