import math
import random
import sys
import pygame

# --------------------------------------------------
# Configuración optimizada
# --------------------------------------------------
WIDTH = 1100
HEIGHT = 550
FPS = 30

COLOR_SKY = (120, 200, 245)
COLOR_SEA = (20, 145, 190)
COLOR_SAND = (235, 205, 135)
COLOR_WAVE = (50, 210, 255)
COLOR_WAVE_CORE = (255, 255, 255)

MAP_SCROLL_SPEED = 0.0025
PARTICLE_SCROLL_MULTIPLIER = 0.15

# Movimiento
PLAYER_MAX_SPEED = 4.0
KEYBOARD_SPEED = 4.0
MOUSE_LERP = 0.06

# --------------------------------------------------
# Estado del juego
# --------------------------------------------------
surfer_x = 180
surfer_y = HEIGHT / 2
offset_mapa = 0.0
grosor_camino = 110
energia = 100.0
puntaje = 0
game_over = False

max_particulas = 40
particulas = []

# --------------------------------------------------
# Inicialización
# --------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Beach Surfer Refactor")
clock = pygame.time.Clock()

font_hud = pygame.font.SysFont("arial", 18, bold=True)
font_small = pygame.font.SysFont("arial", 14)
font_go_big = pygame.font.SysFont("arial", 42, bold=True)
font_go_mid = pygame.font.SysFont("arial", 22, bold=True)
font_go_small = pygame.font.SysFont("arial", 16)

# --------------------------------------------------
# Utilidades
# --------------------------------------------------


def salir_del_juego():
    pygame.quit()
    sys.exit()


def lerp(a, b, t):
    return a + (b - a) * t


def map_value(value, in_min, in_max, out_min, out_max):
    return out_min + (float(value - in_min) / float(in_max - in_min)) * (out_max - out_min)


def draw_text(surface, text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# --------------------------------------------------
# Capa de entrada abstracta
# --------------------------------------------------


class InputState:
    def __init__(self):
        self.mode = "mouse"  # mouse | keyboard
        self.vertical_axis = 0.0  # -1.0 arriba, +1.0 abajo
        self.mouse_target_y = None
        self.confirm_pressed = False
        self.back_pressed = False
        self.quit_requested = False


class InputManager:
    def __init__(self):
        self.state = InputState()

    def begin_frame(self):
        self.state.confirm_pressed = False
        self.state.back_pressed = False
        self.state.quit_requested = False
        self.state.vertical_axis = 0.0
        self.state.mouse_target_y = None

    def process_events(self):
        keys = pygame.key.get_pressed()

        if self.state.mode == "keyboard":
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.state.vertical_axis = -1.0
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.state.vertical_axis = 1.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state.quit_requested = True

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.state.quit_requested = True
                    self.state.back_pressed = True

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.state.confirm_pressed = True

                elif event.key == pygame.K_F1:
                    self.state.mode = "mouse"

                elif event.key == pygame.K_F2:
                    self.state.mode = "keyboard"

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.state.confirm_pressed = True

        if self.state.mode == "mouse":
            _, mouse_y = pygame.mouse.get_pos()
            self.state.mouse_target_y = mouse_y

        return self.state


input_manager = InputManager()

# --------------------------------------------------
# Ruta
# --------------------------------------------------


def ruta_y(x, offset):
    v = (
        math.sin(offset * 1.2 + x * 0.0018) * 0.55 +
        math.sin(offset * 0.7 + x * 0.0009 + 1.3) * 0.30 +
        math.sin(offset * 1.8 + x * 0.0026 + 2.1) * 0.15
    )
    norm = (v + 1.0) / 2.0
    return norm * (HEIGHT - 220) + 110


def get_ruta_puntos():
    puntos = []
    step = 30
    for x in range(0, WIDTH + 1, step):
        puntos.append((x, ruta_y(x, offset_mapa)))
    return puntos

# --------------------------------------------------
# Fondo precalculado
# --------------------------------------------------


def crear_fondo():
    fondo = pygame.Surface((WIDTH, HEIGHT))
    horizon = int(HEIGHT * 0.45)
    sea_bottom = int(HEIGHT * 0.82)

    pygame.draw.rect(fondo, COLOR_SKY, (0, 0, WIDTH, horizon))
    pygame.draw.rect(fondo, COLOR_SEA, (0, horizon,
                     WIDTH, sea_bottom - horizon))
    pygame.draw.rect(fondo, COLOR_SAND,
                     (0, sea_bottom, WIDTH, HEIGHT - sea_bottom))

    pygame.draw.circle(fondo, (255, 235, 120), (WIDTH - 130, 90), 35)
    pygame.draw.line(fondo, (255, 255, 255), (0, horizon), (WIDTH, horizon), 2)

    dibujar_palmera_estatica(fondo, 100, HEIGHT - 5, 1.0)
    dibujar_palmera_estatica(fondo, WIDTH - 120, HEIGHT - 5, 0.9)

    for i in range(0, WIDTH, 40):
        pygame.draw.arc(fondo, (220, 190, 120),
                        (i, sea_bottom + 8, 30, 10), 0, math.pi, 1)

    return fondo


def dibujar_palmera_estatica(surface, x, base_y, scale=1.0):
    trunk = (120, 80, 40)
    leaf = (30, 130, 60)

    top_y = base_y - int(85 * scale)
    pygame.draw.line(surface, trunk, (x, base_y),
                     (x - int(10 * scale), top_y), int(8 * scale))

    cx = x - int(10 * scale)
    cy = top_y
    for dx, dy in [(-45, -20), (-25, -30), (0, -35), (25, -28), (45, -15)]:
        pygame.draw.line(surface, leaf, (cx, cy), (cx +
                         int(dx * scale), cy + int(dy * scale)), int(4 * scale))


fondo_estatico = crear_fondo()

# --------------------------------------------------
# Partículas
# --------------------------------------------------


def init_particulas():
    global particulas
    particulas = []
    for _ in range(max_particulas):
        x = random.uniform(0, WIDTH)
        y = random.uniform(HEIGHT * 0.45, HEIGHT * 0.82)
        z = random.uniform(1, 4)
        particulas.append([x, y, z])


def dibujar_particulas(surface):
    for p in particulas:
        x, y, z = p
        r = max(1, int(z))
        pygame.draw.circle(surface, (240, 250, 255), (int(x), int(y)), r)

        p[0] -= z * PARTICLE_SCROLL_MULTIPLIER
        if p[0] < 0:
            p[0] = WIDTH
            p[1] = random.uniform(HEIGHT * 0.45, HEIGHT * 0.82)

# --------------------------------------------------
# Ola
# --------------------------------------------------


def dibujar_ruta_ola(surface):
    puntos = get_ruta_puntos()
    pygame.draw.lines(surface, (120, 235, 255), False, puntos, grosor_camino)
    pygame.draw.lines(surface, COLOR_WAVE, False,
                      puntos, max(1, grosor_camino - 18))
    pygame.draw.lines(surface, COLOR_WAVE_CORE, False, puntos, 3)

# --------------------------------------------------
# Surfista
# --------------------------------------------------


def dibujar_surfista(surface, x, y):
    pygame.draw.ellipse(surface, (255, 255, 255), (x - 70, y + 10, 45, 14))
    pygame.draw.ellipse(surface, (255, 120, 60), (x - 55, y + 8, 110, 20))

    pygame.draw.line(surface, (50, 35, 20), (x - 4, y), (x - 8, y + 18), 3)
    pygame.draw.line(surface, (50, 35, 20), (x + 8, y), (x + 12, y + 18), 3)

    pygame.draw.rect(surface, (30, 90, 200),
                     (x - 10, y - 10, 22, 15), border_radius=3)
    pygame.draw.rect(surface, (215, 160, 110),
                     (x - 9, y - 32, 20, 22), border_radius=4)

    pygame.draw.line(surface, (215, 160, 110),
                     (x - 7, y - 24), (x - 22, y - 12), 3)
    pygame.draw.line(surface, (215, 160, 110),
                     (x + 9, y - 24), (x + 22, y - 30), 3)

    pygame.draw.circle(surface, (220, 170, 120), (int(x), int(y - 45)), 9)
    pygame.draw.arc(surface, (70, 40, 20), (x - 10, y -
                    55, 20, 15), math.pi, math.pi * 2, 3)

# --------------------------------------------------
# HUD y estados
# --------------------------------------------------


def dibujar_hud(surface, control_mode):
    pygame.draw.rect(surface, (0, 60, 90), (0, 0, WIDTH, 62))
    pygame.draw.line(surface, (255, 255, 255), (0, 50), (WIDTH, 50), 1)

    draw_text(surface, "BEACH SURFER", font_hud, (255, 255, 255), 25, 12)
    draw_text(surface, f"SCORE: {puntaje}",
              font_hud, (255, 255, 255), WIDTH - 180, 12)
    draw_text(surface, "BALANCE", font_hud, (255, 255, 255), 420, 12)

    pygame.draw.rect(surface, (255, 255, 255), (510, 12, 160, 18), 1)
    bar_w = int(map_value(energia, 0, 100, 0, 154))
    color = (80, 255, 140) if energia > 45 else (255, 90, 90)
    pygame.draw.rect(surface, color, (513, 15, max(0, bar_w), 12))

    draw_text(surface, "ESC/Q salir", font_small,
              (255, 255, 255), WIDTH - 120, 34)
    draw_text(surface, f"Modo: {control_mode}",
              font_small, (255, 255, 255), 25, 36)
    draw_text(surface, "F1 mouse  F2 wearable/teclado",
              font_small, (255, 255, 255), 130, 36)


def dibujar_efecto_dano(surface):
    pygame.draw.rect(surface, (255, 100, 100), (0, 0, WIDTH, HEIGHT), 10)


def dibujar_pantalla_game_over(surface, control_mode):
    surface.fill((255, 220, 160))
    draw_text(surface, "WIPEOUT!", font_go_big, (0, 90, 140),
              WIDTH // 2, HEIGHT // 2 - 40, center=True)
    draw_text(surface, "Perdiste el balance y saliste de la ola.",
              font_go_small, (60, 60, 60), WIDTH // 2, HEIGHT // 2 + 5, center=True)
    draw_text(surface, f"PUNTAJE: {puntaje}", font_go_mid,
              (0, 120, 180), WIDTH // 2, HEIGHT // 2 + 45, center=True)
    draw_text(surface, "Click o ENTER para reiniciar", font_go_small,
              (80, 80, 80), WIDTH // 2, HEIGHT // 2 + 100, center=True)
    draw_text(surface, "ESC / Q para salir", font_go_small,
              (80, 80, 80), WIDTH // 2, HEIGHT // 2 + 125, center=True)
    draw_text(surface, f"Modo actual: {control_mode}", font_go_small,
              (80, 80, 80), WIDTH // 2, HEIGHT // 2 + 150, center=True)

# --------------------------------------------------
# Movimiento desacoplado
# --------------------------------------------------


def actualizar_surfer_por_input(input_state):
    global surfer_y

    if input_state.mode == "mouse" and input_state.mouse_target_y is not None:
        objetivo_y = lerp(surfer_y, input_state.mouse_target_y, MOUSE_LERP)
        delta = objetivo_y - surfer_y

        if delta > PLAYER_MAX_SPEED:
            delta = PLAYER_MAX_SPEED
        elif delta < -PLAYER_MAX_SPEED:
            delta = -PLAYER_MAX_SPEED

        surfer_y += delta

    elif input_state.mode == "keyboard":
        surfer_y += input_state.vertical_axis * KEYBOARD_SPEED

    surfer_y = max(60, min(HEIGHT - 60, surfer_y))

# --------------------------------------------------
# Reinicio
# --------------------------------------------------


def reiniciar_juego():
    global energia, puntaje, game_over, surfer_y, offset_mapa
    energia = 100.0
    puntaje = 0
    game_over = False
    surfer_y = HEIGHT / 2
    offset_mapa = 0.0

# --------------------------------------------------
# Main loop
# --------------------------------------------------


def main():
    global surfer_y, offset_mapa, energia, puntaje, game_over

    init_particulas()

    while True:
        input_manager.begin_frame()
        input_state = input_manager.process_events()

        if input_state.quit_requested:
            salir_del_juego()

        if game_over:
            if input_state.confirm_pressed:
                reiniciar_juego()
        else:
            actualizar_surfer_por_input(input_state)

            screen.blit(fondo_estatico, (0, 0))
            dibujar_particulas(screen)
            dibujar_ruta_ola(screen)

            centro_ruta = ruta_y(surfer_x, offset_mapa)
            distancia_al_centro = abs(surfer_y - centro_ruta)

            if distancia_al_centro > grosor_camino / 2:
                energia -= 0.6
                dibujar_efecto_dano(screen)
                if energia <= 0:
                    energia = 0
                    game_over = True
            else:
                puntaje += 2

            dibujar_surfista(screen, surfer_x, surfer_y)
            dibujar_hud(screen, input_state.mode)

            offset_mapa += MAP_SCROLL_SPEED

        if game_over:
            dibujar_pantalla_game_over(screen, input_state.mode)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
