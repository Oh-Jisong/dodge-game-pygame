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
pygame.display.set_caption("Dodge Game v2")

clock = pygame.time.Clock()
FPS = 60

BLACK = (0, 0, 0)
WHITE = (245, 245, 245)

RED = (235, 70, 70)
GOLD_OUTER = (220, 175, 55)
GOLD_INNER = (255, 215, 80)
GOLD_RIM = (255, 235, 150)
GREEN = (70, 220, 120)
BLUE = (90, 170, 255)
PURPLE = (190, 120, 255)
CYAN = (120, 235, 255)

font = pygame.font.SysFont(None, 34)
big_font = pygame.font.SysFont(None, 84)
mid_font = pygame.font.SysFont(None, 44)

SAVE_PATH = Path("best_time.txt")


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def draw_text_center(text, y, color=WHITE, use_big=False, use_mid=False):
    f = big_font if use_big else (mid_font if use_mid else font)
    surf = f.render(text, True, color)
    screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))


def draw_bar(x, y, w, h, value01, fg_color, bg_color=(35, 35, 35)):
    pygame.draw.rect(screen, bg_color, (x, y, w, h))
    fill = int(w * clamp(value01, 0.0, 1.0))
    pygame.draw.rect(screen, fg_color, (x, y, fill, h))
    pygame.draw.rect(screen, (70, 70, 70), (x, y, w, h), 2)


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


# -------------------------
# Coin drawing
# -------------------------
def draw_coin(surface, rect: pygame.Rect):
    cx, cy = rect.center
    r = min(rect.width, rect.height) // 2

    pygame.draw.circle(surface, GOLD_OUTER, (cx, cy), r)
    pygame.draw.circle(surface, GOLD_INNER, (cx, cy), int(r * 0.82))
    pygame.draw.circle(surface, GOLD_RIM, (cx, cy), int(r * 0.70), 2)

    hl_r = max(2, int(r * 0.22))
    pygame.draw.circle(surface, (255, 245, 210), (cx - int(r * 0.25), cy - int(r * 0.25)), hl_r)

    line_color = (235, 195, 85)
    pygame.draw.line(
        surface,
        line_color,
        (cx - int(r * 0.18), cy - int(r * 0.35)),
        (cx - int(r * 0.18), cy + int(r * 0.35)),
        2,
    )


# -------------------------
# Particles
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
# Starfield background (parallax)
# -------------------------
@dataclass
class Star:
    x: float
    y: float
    speed: float
    size: int
    color: tuple

    def update(self, dt, world_speed_mul):
        self.y += self.speed * world_speed_mul * dt
        if self.y > HEIGHT + 20:
            self.y = -random.uniform(10, 120)
            self.x = random.uniform(0, WIDTH)

    def draw(self, surf, ox=0, oy=0):
        pygame.draw.circle(surf, self.color, (int(self.x + ox), int(self.y + oy)), self.size)


# -------------------------
# Game objects
# -------------------------
@dataclass
class Obstacle:
    rect: pygame.Rect
    speed: float
    amp: float
    freq: float
    phase: float
    base_x: float

    def update(self, dt, t, world_speed_mul):
        self.rect.y += int(self.speed * world_speed_mul * dt)
        if self.amp > 0:
            # side-to-side wobble
            self.rect.x = int(self.base_x + math.sin((t + self.phase) * self.freq) * self.amp)

    def draw(self, surf, ox=0, oy=0):
        pygame.draw.rect(surf, RED, self.rect.move(ox, oy), border_radius=8)


@dataclass
class Coin:
    rect: pygame.Rect
    speed: float

    def update(self, dt, world_speed_mul):
        self.rect.y += int(self.speed * world_speed_mul * dt)

    def draw(self, surf, ox=0, oy=0):
        draw_coin(surf, self.rect.move(ox, oy))


@dataclass
class PowerUp:
    kind: str  # "SHIELD" | "SLOW"
    rect: pygame.Rect
    speed: float

    def update(self, dt, world_speed_mul):
        self.rect.y += int(self.speed * world_speed_mul * dt)

    def draw(self, surf, ox=0, oy=0):
        r = self.rect.move(ox, oy)
        if self.kind == "SHIELD":
            pygame.draw.rect(surf, PURPLE, r, border_radius=10)
            pygame.draw.rect(surf, (240, 220, 255), r.inflate(-10, -10), 2, border_radius=8)
        else:
            pygame.draw.rect(surf, CYAN, r, border_radius=10)
            pygame.draw.rect(surf, (230, 255, 255), r.inflate(-10, -10), 2, border_radius=8)


# -------------------------
# Spawners
# -------------------------
def spawn_obstacle(level: int) -> Obstacle:
    w = random.randint(34, 90)
    h = random.randint(34, 90)
    x = random.randint(0, WIDTH - w)
    y = -h

    speed = 235 + level * 20 + random.randint(-25, 45)

    # add wobble more often at higher levels
    wobble_chance = clamp(0.20 + level * 0.03, 0.20, 0.70)
    if random.random() < wobble_chance:
        amp = random.uniform(35, 120) * clamp(level / 6.0, 0.3, 1.0)
        freq = random.uniform(1.6, 3.0)
        phase = random.uniform(0, 10)
    else:
        amp, freq, phase = 0.0, 0.0, 0.0

    return Obstacle(pygame.Rect(x, y, w, h), speed, amp, freq, phase, float(x))


def spawn_coin(level: int) -> Coin:
    size = random.randint(22, 30)
    x = random.randint(0, WIDTH - size)
    y = -size
    speed = 250 + level * 11 + random.randint(-10, 25)
    return Coin(pygame.Rect(x, y, size, size), speed)


def spawn_powerup(level: int) -> PowerUp:
    size = 28
    x = random.randint(0, WIDTH - size)
    y = -size
    speed = 245 + level * 9 + random.randint(-10, 20)
    kind = "SHIELD" if random.random() < 0.55 else "SLOW"
    return PowerUp(kind, pygame.Rect(x, y, size, size), speed)


# -------------------------
# Game (v2)
# -------------------------
class Game:
    def __init__(self):
        self.best_time = load_best()
        self.reset_all()

    def reset_all(self):
        self.state = "MENU"  # MENU / PLAY
        self.game = self.reset_game()

        # input edge tracking
        self.p_was = False
        self.shift_was = False
        self.space_was = False

        # background
        self.stars_far = self.make_stars(55, speed_range=(30, 60), size_range=(1, 2), tint=(110, 110, 110))
        self.stars_mid = self.make_stars(40, speed_range=(70, 120), size_range=(1, 3), tint=(160, 160, 160))
        self.stars_near = self.make_stars(18, speed_range=(160, 240), size_range=(2, 3), tint=(220, 220, 220))

    def reset_game(self):
        player = pygame.Rect(WIDTH // 2 - 25, HEIGHT - 95, 50, 50)

        # Movement smoothing (accel)
        player_speed = 310.0
        vel_x = 0.0
        accel = 2600.0
        friction = 3600.0

        # Dash
        dash_speed = 740.0
        dash_duration = 0.12
        dash_cooldown = 0.55
        dash_until = 0.0
        dash_cd_until = 0.0

        # Core
        hp = 3
        invincible_until = 0.0

        # v2 powerups
        shield = 0  # hit buffer
        slow_until = 0.0

        # scoring
        score = 0
        combo = 0
        combo_timer = 0.0
        combo_keep = 2.0

        t = 0.0

        obstacles = []
        coins = []
        powerups = []
        particles = []

        obs_timer = 0.0
        coin_timer = 0.0
        pu_timer = 0.0

        paused = False
        game_over = False

        # screen shake / flash
        shake = 0.0
        flash = 0.0

        return {
            "player": player,
            "player_speed": player_speed,
            "vel_x": vel_x,
            "accel": accel,
            "friction": friction,
            "dash_speed": dash_speed,
            "dash_duration": dash_duration,
            "dash_cooldown": dash_cooldown,
            "dash_until": dash_until,
            "dash_cd_until": dash_cd_until,
            "hp": hp,
            "invincible_until": invincible_until,
            "shield": shield,
            "slow_until": slow_until,
            "score": score,
            "combo": combo,
            "combo_timer": combo_timer,
            "combo_keep": combo_keep,
            "t": t,
            "obstacles": obstacles,
            "coins": coins,
            "powerups": powerups,
            "particles": particles,
            "obs_timer": obs_timer,
            "coin_timer": coin_timer,
            "pu_timer": pu_timer,
            "paused": paused,
            "game_over": game_over,
            "shake": shake,
            "flash": flash,
        }

    def make_stars(self, n, speed_range, size_range, tint):
        stars = []
        for _ in range(n):
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            spd = random.uniform(*speed_range)
            size = random.randint(*size_range)
            # slight random brightness
            d = random.randint(-20, 20)
            col = (clamp(tint[0] + d, 60, 255), clamp(tint[1] + d, 60, 255), clamp(tint[2] + d, 60, 255))
            stars.append(Star(x, y, spd, size, col))
        return stars

    def quit(self):
        pygame.quit()
        sys.exit()

    def world_speed_mul(self):
        # SLOW powerup effect
        now_t = self.game["t"]
        if now_t < self.game["slow_until"]:
            # ease in/out
            remain = self.game["slow_until"] - now_t
            t = clamp(remain / 3.0, 0.0, 1.0)
            return lerp(0.55, 1.0, 1.0 - t)  # slower near the start, back to 1
        return 1.0

    def update_best(self):
        if (not self.game["game_over"]) and (self.game["t"] > self.best_time):
            self.best_time = self.game["t"]
            save_best(self.best_time)

    def apply_hit(self):
        g = self.game

        if g["shield"] > 0:
            g["shield"] -= 1
            g["invincible_until"] = g["t"] + 0.55
            g["shake"] = max(g["shake"], 10.0)
            g["flash"] = max(g["flash"], 0.18)
            emit_particles(g["particles"], g["player"].centerx, g["player"].centery, PURPLE, count=18, power=260)
            return

        g["hp"] -= 1
        g["invincible_until"] = g["t"] + 0.85
        g["shake"] = max(g["shake"], 14.0)
        g["flash"] = max(g["flash"], 0.22)

        emit_particles(g["particles"], g["player"].centerx, g["player"].centery, RED, count=18, power=260)
        g["combo"] = max(0, g["combo"] - 2)
        g["combo_timer"] = g["combo_keep"] * 0.5 if g["combo"] > 0 else 0.0

        if g["hp"] <= 0:
            g["game_over"] = True

    def update(self, dt):
        g = self.game
        keys = pygame.key.get_pressed()

        if keys[pygame.K_ESCAPE]:
            self.quit()

        # ---------------- MENU ----------------
        if self.state == "MENU":
            space_down = keys[pygame.K_SPACE]
            if space_down and not self.space_was:
                self.game = self.reset_game()
                self.state = "PLAY"
            self.space_was = space_down
            return

        # ---------------- PLAY ----------------
        # Pause toggle
        p_down = keys[pygame.K_p]
        if p_down and not self.p_was and (not g["game_over"]):
            g["paused"] = not g["paused"]
        self.p_was = p_down

        # Game over inputs
        if g["game_over"]:
            if keys[pygame.K_r]:
                self.game = self.reset_game()
                g = self.game
            if keys[pygame.K_m]:
                self.state = "MENU"
            # still update particles & background a bit
            self.update_background(dt)
            self.update_particles(dt * 0.9)
            self.update_shake_flash(dt)
            return

        if g["paused"]:
            self.update_background(dt * 0.25)
            self.update_particles(dt * 0.18)
            self.update_shake_flash(dt * 0.25)
            return

        # time
        g["t"] += dt
        now_t = g["t"]
        level = 1 + int(now_t // 10)

        # world speed
        wmul = self.world_speed_mul()

        # Dash (edge)
        shift_down = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        can_dash = (now_t >= g["dash_cd_until"]) and (now_t >= g["dash_until"])

        if shift_down and not self.shift_was and can_dash:
            g["dash_until"] = now_t + g["dash_duration"]
            g["dash_cd_until"] = now_t + g["dash_cooldown"]
            g["shake"] = max(g["shake"], 6.0)
            emit_particles(g["particles"], g["player"].centerx, g["player"].centery, BLUE, count=10, power=170)

        self.shift_was = shift_down

        # Movement (smooth accel)
        move_dir = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_dir -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_dir += 1

        in_dash = now_t < g["dash_until"]
        max_speed = g["dash_speed"] if in_dash else g["player_speed"]

        if move_dir != 0:
            g["vel_x"] += move_dir * g["accel"] * dt
        else:
            # friction to stop
            if g["vel_x"] > 0:
                g["vel_x"] = max(0.0, g["vel_x"] - g["friction"] * dt)
            elif g["vel_x"] < 0:
                g["vel_x"] = min(0.0, g["vel_x"] + g["friction"] * dt)

        g["vel_x"] = clamp(g["vel_x"], -max_speed, max_speed)
        g["player"].x += int(g["vel_x"] * dt)
        g["player"].x = clamp(g["player"].x, 0, WIDTH - g["player"].width)

        # Spawn: obstacle
        g["obs_timer"] += dt
        obs_interval = max(0.18, 0.58 - level * 0.03)
        if g["obs_timer"] >= obs_interval:
            g["obs_timer"] = 0.0
            g["obstacles"].append(spawn_obstacle(level))

        # Spawn: coin
        g["coin_timer"] += dt
        coin_interval = max(0.42, 0.95 - level * 0.02)
        if g["coin_timer"] >= coin_interval:
            g["coin_timer"] = 0.0
            g["coins"].append(spawn_coin(level))

        # Spawn: powerup (rare)
        g["pu_timer"] += dt
        pu_interval = max(7.5, 13.0 - level * 0.25)
        if g["pu_timer"] >= pu_interval:
            g["pu_timer"] = 0.0
            g["powerups"].append(spawn_powerup(level))

        # Move objects
        for o in g["obstacles"]:
            o.update(dt, now_t, wmul)
        for c in g["coins"]:
            c.update(dt, wmul)
        for pu in g["powerups"]:
            pu.update(dt, wmul)

        # Remove off-screen
        g["obstacles"] = [o for o in g["obstacles"] if o.rect.y < HEIGHT + 170]
        g["coins"] = [c for c in g["coins"] if c.rect.y < HEIGHT + 140]
        g["powerups"] = [p for p in g["powerups"] if p.rect.y < HEIGHT + 160]

        # Combo decay
        if g["combo"] > 0:
            g["combo_timer"] -= dt
            if g["combo_timer"] <= 0:
                g["combo"] = max(0, g["combo"] - 1)
                g["combo_timer"] = g["combo_keep"] * 0.6 if g["combo"] > 0 else 0.0

        # Coin collision
        new_coins = []
        for c in g["coins"]:
            if g["player"].colliderect(c.rect):
                g["combo"] += 1
                g["combo_timer"] = g["combo_keep"]
                mult = 1 + min(g["combo"] // 5, 6)
                # small level scaling
                g["score"] += int(10 * mult * (1.0 + level * 0.06))
                g["shake"] = max(g["shake"], 3.0)
                emit_particles(g["particles"], c.rect.centerx, c.rect.centery, GOLD_INNER, count=12, power=200)
            else:
                new_coins.append(c)
        g["coins"] = new_coins

        # Powerup collision
        new_pu = []
        for pu in g["powerups"]:
            if g["player"].colliderect(pu.rect):
                if pu.kind == "SHIELD":
                    g["shield"] = min(2, g["shield"] + 1)
                    g["score"] += 80 + level * 8
                    emit_particles(g["particles"], pu.rect.centerx, pu.rect.centery, PURPLE, count=16, power=240)
                else:
                    g["slow_until"] = max(g["slow_until"], now_t + 3.2)
                    g["score"] += 70 + level * 6
                    emit_particles(g["particles"], pu.rect.centerx, pu.rect.centery, CYAN, count=16, power=240)
                g["combo"] = max(g["combo"], 2)  # small assist
                g["combo_timer"] = max(g["combo_timer"], 1.2)
                g["shake"] = max(g["shake"], 6.0)
            else:
                new_pu.append(pu)
        g["powerups"] = new_pu

        # Obstacle collision (invincibility)
        invincible = now_t < g["invincible_until"]
        if not invincible:
            for o in g["obstacles"]:
                if g["player"].colliderect(o.rect):
                    self.apply_hit()
                    break

        # background/particles/shake
        self.update_background(dt)
        self.update_particles(dt)
        self.update_shake_flash(dt)

        # Best time update
        self.update_best()

    def update_background(self, dt):
        wmul = self.world_speed_mul()
        for s in self.stars_far:
            s.update(dt, wmul * 0.5)
        for s in self.stars_mid:
            s.update(dt, wmul * 0.85)
        for s in self.stars_near:
            s.update(dt, wmul * 1.1)

    def update_particles(self, dt):
        g = self.game
        for p in g["particles"]:
            p.update(dt)
        g["particles"] = [p for p in g["particles"] if p.alive()]

    def update_shake_flash(self, dt):
        g = self.game
        g["shake"] = max(0.0, g["shake"] - 26.0 * dt)
        g["flash"] = max(0.0, g["flash"] - 2.8 * dt)

    def render(self):
        g = self.game

        # shake offset
        ox = oy = 0
        if g["shake"] > 0:
            amp = g["shake"]
            ox = int(random.uniform(-amp, amp))
            oy = int(random.uniform(-amp * 0.7, amp * 0.7))

        screen.fill(BLACK)

        # background stars
        for s in self.stars_far:
            s.draw(screen, ox=ox, oy=oy)
        for s in self.stars_mid:
            s.draw(screen, ox=ox, oy=oy)
        for s in self.stars_near:
            s.draw(screen, ox=ox, oy=oy)

        if self.state == "MENU":
            draw_text_center("DODGE GAME", 150, use_big=True)
            draw_text_center("Press SPACE to Start", 290, color=GOLD_INNER, use_mid=True)
            draw_text_center("Move: LEFT/RIGHT or A/D   Dash: SHIFT   Pause: P", 360)
            draw_text_center("Coins = Score + Combo | PowerUps: Shield / Slow", 402)
            draw_text_center("Red blocks = Damage", 444)
            draw_text_center(f"Best Time: {self.best_time:.1f}s", 510, color=GREEN)
            pygame.display.flip()
            return

        # objects
        for o in g["obstacles"]:
            o.draw(screen, ox=ox, oy=oy)
        for c in g["coins"]:
            c.draw(screen, ox=ox, oy=oy)
        for pu in g["powerups"]:
            pu.draw(screen, ox=ox, oy=oy)
        for p in g["particles"]:
            p.draw(screen)

        # player
        invincible = g["t"] < g["invincible_until"]
        if (not invincible) or (int(g["t"] * 12) % 2 == 0):
            pygame.draw.rect(screen, GREEN, g["player"].move(ox, oy), border_radius=10)

        # v2: shield ring visual
        if g["shield"] > 0:
            cx, cy = g["player"].center
            r = 36
            pygame.draw.circle(screen, PURPLE, (cx + ox, cy + oy), r, 3)

        # HUD
        level = 1 + int(g["t"] // 10)
        ui_time = font.render(f"Time: {g['t']:.1f}s", True, WHITE)
        ui_level = font.render(f"Level: {level}", True, WHITE)
        ui_hp = font.render(f"HP: {g['hp']}", True, WHITE)
        ui_score = font.render(f"Score: {g['score']}", True, WHITE)
        ui_combo = font.render(f"Combo: {g['combo']}", True, GOLD_INNER if g["combo"] > 0 else WHITE)
        ui_best = font.render(f"Best: {self.best_time:.1f}s", True, GREEN)
        ui_shield = font.render(f"Shield: {g['shield']}", True, PURPLE if g["shield"] > 0 else (160, 160, 160))

        screen.blit(ui_time, (20, 16))
        screen.blit(ui_level, (20, 48))
        screen.blit(ui_hp, (20, 80))
        screen.blit(ui_score, (20, 112))
        screen.blit(ui_combo, (20, 144))
        screen.blit(ui_shield, (20, 176))
        screen.blit(ui_best, (20, 208))

        # Dash bar
        now_t = g["t"]
        dash_ready = 1.0
        if now_t < g["dash_cd_until"]:
            remain = g["dash_cd_until"] - now_t
            dash_ready = 1.0 - clamp(remain / g["dash_cooldown"], 0.0, 1.0)

        dash_label = font.render("Dash", True, BLUE)
        screen.blit(dash_label, (WIDTH - 170, 16))
        draw_bar(WIDTH - 170, 46, 140, 18, dash_ready, BLUE)

        # Slow indicator
        if now_t < g["slow_until"]:
            remain = g["slow_until"] - now_t
            slow01 = clamp(remain / 3.2, 0.0, 1.0)
            slow_label = font.render("Slow", True, CYAN)
            screen.blit(slow_label, (WIDTH - 170, 78))
            draw_bar(WIDTH - 170, 108, 140, 18, slow01, CYAN)

        tip = font.render("SHIFT: Dash | P: Pause | R: Restart | M: Menu | ESC: Quit", True, (170, 170, 170))
        screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 36))

        if g["paused"] and not g["game_over"]:
            draw_text_center("PAUSED", HEIGHT // 2 - 90, use_big=True)
            draw_text_center("Press P to Resume", HEIGHT // 2 + 10, color=GOLD_INNER)

        if g["game_over"]:
            draw_text_center("GAME OVER", HEIGHT // 2 - 120, use_big=True)
            draw_text_center("R: Restart   M: Menu   ESC: Quit", HEIGHT // 2 - 20, color=GOLD_INNER)

        # flash overlay
        if g["flash"] > 0:
            a = int(255 * clamp(g["flash"], 0.0, 0.25) / 0.25)
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, a))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()


def main():
    game = Game()

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.quit()

        game.update(dt)
        game.render()


if __name__ == "__main__":
    main()