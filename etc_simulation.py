"""
ETC & Chemiosmosis Interactive Simulation
==========================================
Pygame-based simulation of the mitochondrial electron transport chain.
Features: animated electrons/protons, chemical inhibitor database,
drag-and-drop chemicals, info panels, step-through mode.

Mechanism flow:
  NADH -> CI (pumps 4H+) -> CoQ carries e- laterally in membrane -> CIII (pumps 4H+)
  -> Cyt c carries e- along IMS -> CIV (pumps 2H+, reduces O2 to H2O)
  FADH2 -> CII (no pump) -> CoQ -> CIII -> Cyt c -> CIV
  H+ accumulate in IMS, flow back through CV (ATP synthase) to make ATP
"""

import pygame
import json
import math
import random
import os
import sys

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 1280, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mitochondrial ETC & Chemiosmosis Simulation")

clock = pygame.time.Clock()
FPS = 60

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BG_COLOR = (18, 18, 24)
MEMBRANE_COLOR = (70, 60, 45)
MEMBRANE_EDGE = (160, 180, 200)
IMS_COLOR = (30, 35, 50)
MATRIX_COLOR = (20, 22, 30)
TEXT_COLOR = (220, 220, 220)
LABEL_DIM = (150, 150, 150)
SIDEBAR_BG = (22, 22, 32)
SIDEBAR_HIGHLIGHT = (40, 40, 60)
BUTTON_COLOR = (50, 50, 70)
BUTTON_HOVER = (70, 70, 100)
ACCENT = (255, 202, 40)

CI_GREEN = (56, 142, 60)
CI_GREEN_LIGHT = (76, 175, 80)
CII_RED = (198, 40, 40)
CII_RED_LIGHT = (239, 83, 80)
CIII_TEAL = (0, 121, 107)
CIII_TEAL_LIGHT = (0, 150, 136)
CIV_RED = (183, 28, 28)
CIV_RED_LIGHT = (229, 57, 53)
CV_YELLOW = (255, 179, 0)
CV_YELLOW_LIGHT = (255, 202, 40)
CV_PURPLE = (142, 36, 170)

COQ_ORANGE = (230, 126, 34)
CYTC_BLUE = (25, 42, 86)
CYTC_BLUE_LIGHT = (60, 80, 140)
ELECTRON_COLOR = (255, 234, 0)
PROTON_COLOR = (0, 229, 255)
ATP_COLOR = (255, 202, 40)
ROS_COLOR = (255, 50, 50)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_SM = pygame.font.SysFont("Segoe UI", 13)
FONT_MD = pygame.font.SysFont("Segoe UI", 16)
FONT_LG = pygame.font.SysFont("Segoe UI", 20, bold=True)
FONT_XL = pygame.font.SysFont("Segoe UI", 26, bold=True)
FONT_TITLE = pygame.font.SysFont("Segoe UI", 14, bold=True)
FONT_TINY = pygame.font.SysFont("Segoe UI", 11)

# ---------------------------------------------------------------------------
# Load Chemical Database
# ---------------------------------------------------------------------------
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chemicals_db.json")
with open(db_path, "r", encoding="utf-8") as f:
    CHEM_DB = json.load(f)

CHEMICALS = CHEM_DB["chemicals"]

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
MEMBRANE_Y = 380
MEMBRANE_H = 60
SIDEBAR_W = 280
SIM_X = SIDEBAR_W
SIM_W = WIDTH - SIDEBAR_W

IMS_TOP = 0
IMS_BOTTOM = MEMBRANE_Y - MEMBRANE_H // 2   # top edge of membrane
MATRIX_TOP = MEMBRANE_Y + MEMBRANE_H // 2   # bottom edge of membrane
MATRIX_BOTTOM = HEIGHT

# Complex positions
CX = {
    "CI":   SIM_X + 120,
    "CII":  SIM_X + 260,
    "CIII": SIM_X + 420,
    "CIV":  SIM_X + 600,
    "CV":   SIM_X + 790,
}

# Max protons that accumulate visibly in IMS before we stop adding more
IMS_PROTON_CAP = 100

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_rounded_rect(surface, color, rect, radius=8, alpha=None):
    if alpha is not None:
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
        surface.blit(s, (rect[0], rect[1]))
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current = ""
    for w in words:
        test = current + (" " if current else "") + w
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Complex drawing functions
# ---------------------------------------------------------------------------
def draw_complex_I(surf, cx, cy, blocked=False, highlight=False, active=False):
    body = pygame.Rect(cx - 35, cy - 70, 70, 140)
    arm = pygame.Rect(cx - 75, cy + 20, 55, 50)
    col = CI_GREEN_LIGHT if highlight else CI_GREEN
    if active:
        col = (min(255, col[0] + 40), min(255, col[1] + 40), min(255, col[2] + 40))
    col_dark = (max(0, col[0] - 20), max(0, col[1] - 20), max(0, col[2] - 20))
    pygame.draw.rect(surf, col, body, border_radius=12)
    pygame.draw.rect(surf, col, arm, border_radius=10)
    pygame.draw.rect(surf, col_dark, (body.x + 2, body.y + 2, body.w - 4, 30), border_radius=10)
    txt = FONT_MD.render("CI", True, (255, 255, 255))
    surf.blit(txt, (cx - txt.get_width() // 2, cy - 8))
    txt2 = FONT_TINY.render("NADH \u2192 NAD\u207a", True, (200, 255, 200))
    surf.blit(txt2, (cx - 70, cy + 75))
    # Pump label
    txt3 = FONT_TINY.render("4 H\u207a \u2191", True, PROTON_COLOR)
    surf.blit(txt3, (cx - txt3.get_width() // 2, cy - 85))
    if blocked:
        _draw_block_x(surf, cx, cy)


def draw_complex_II(surf, cx, cy, blocked=False, highlight=False, active=False):
    col = CII_RED_LIGHT if highlight else CII_RED
    if active:
        col = (min(255, col[0] + 40), min(255, col[1] + 40), min(255, col[2] + 40))
    py = cy + 50
    pygame.draw.ellipse(surf, col, (cx - 30, py - 22, 60, 44))
    pygame.draw.ellipse(surf, (min(255, col[0] + 30), min(255, col[1] + 20), min(255, col[2] + 20)),
                        (cx - 22, py - 16, 44, 32))
    txt = FONT_MD.render("CII", True, (255, 255, 255))
    surf.blit(txt, (cx - txt.get_width() // 2, py - 8))
    txt2 = FONT_TINY.render("FADH\u2082 \u2192 FAD", True, (255, 180, 180))
    surf.blit(txt2, (cx - 28, py + 28))
    txt3 = FONT_TINY.render("(no H\u207a pump)", True, LABEL_DIM)
    surf.blit(txt3, (cx - txt3.get_width() // 2, py - 38))
    if blocked:
        _draw_block_x(surf, cx, py)


def draw_complex_III(surf, cx, cy, blocked=False, highlight=False, active=False):
    col = CIII_TEAL_LIGHT if highlight else CIII_TEAL
    if active:
        col = (min(255, col[0] + 40), min(255, col[1] + 40), min(255, col[2] + 40))
    body = pygame.Rect(cx - 30, cy - 60, 60, 120)
    pygame.draw.rect(surf, col, body, border_radius=14)
    pygame.draw.ellipse(surf, (min(255, col[0] + 20), min(255, col[1] + 20), min(255, col[2] + 20)),
                        (cx - 35, cy - 65, 70, 40))
    txt = FONT_MD.render("CIII", True, (255, 255, 255))
    surf.blit(txt, (cx - txt.get_width() // 2, cy - 8))
    txt3 = FONT_TINY.render("4 H\u207a \u2191", True, PROTON_COLOR)
    surf.blit(txt3, (cx - txt3.get_width() // 2, cy - 80))
    if blocked:
        _draw_block_x(surf, cx, cy)


def draw_complex_IV(surf, cx, cy, blocked=False, highlight=False, active=False):
    col = CIV_RED_LIGHT if highlight else CIV_RED
    if active:
        col = (min(255, col[0] + 40), min(255, col[1] + 40), min(255, col[2] + 40))
    body = pygame.Rect(cx - 28, cy - 50, 56, 100)
    pygame.draw.rect(surf, col, body, border_radius=12)
    pygame.draw.ellipse(surf, (min(255, col[0] + 30), min(255, col[1] + 30), min(255, col[2] + 30)),
                        (cx - 32, cy - 55, 64, 30))
    txt = FONT_MD.render("CIV", True, (255, 255, 255))
    surf.blit(txt, (cx - txt.get_width() // 2, cy - 8))
    txt2 = FONT_TINY.render("\u00bdO\u2082 + 2H\u207a \u2192 H\u2082O", True, (255, 200, 200))
    surf.blit(txt2, (cx - 35, cy + 55))
    txt3 = FONT_TINY.render("2 H\u207a \u2191", True, PROTON_COLOR)
    surf.blit(txt3, (cx - txt3.get_width() // 2, cy - 68))
    if blocked:
        _draw_block_x(surf, cx, cy)


def draw_complex_V(surf, cx, cy, rotation=0, blocked=False, highlight=False):
    col_head = CV_YELLOW_LIGHT if highlight else CV_YELLOW
    col_stalk = CV_PURPLE
    head_y = cy + 45
    pygame.draw.ellipse(surf, col_head, (cx - 35, head_y - 25, 70, 50))
    pygame.draw.rect(surf, col_stalk, (cx - 8, cy - 30, 16, 75), border_radius=4)
    rotor_y = cy - 15
    pygame.draw.circle(surf, (min(255, col_stalk[0] + 40), min(255, col_stalk[1] + 20),
                               min(255, col_stalk[2] + 40)), (cx, rotor_y), 22)
    for i in range(3):
        angle = rotation + i * (2 * math.pi / 3)
        ex = cx + int(18 * math.cos(angle))
        ey = rotor_y + int(18 * math.sin(angle))
        pygame.draw.line(surf, (255, 255, 255), (cx, rotor_y), (ex, ey), 2)
    pygame.draw.rect(surf, col_stalk, (cx - 18, cy - 45, 36, 20), border_radius=6)
    txt = FONT_MD.render("CV", True, (255, 255, 255))
    surf.blit(txt, (cx - txt.get_width() // 2, head_y - 10))
    txt2 = FONT_TINY.render("ATP Synthase", True, (255, 220, 100))
    surf.blit(txt2, (cx - txt2.get_width() // 2, head_y + 30))
    # ADP + Pi -> ATP label
    txt3 = FONT_TINY.render("ADP + P\u1d62 \u2192 ATP", True, ATP_COLOR)
    surf.blit(txt3, (cx - txt3.get_width() // 2, head_y + 44))
    if blocked:
        _draw_block_x(surf, cx, cy)


def _draw_block_x(surf, cx, cy):
    pygame.draw.line(surf, (239, 83, 80), (cx - 25, cy - 25), (cx + 25, cy + 25), 4)
    pygame.draw.line(surf, (239, 83, 80), (cx + 25, cy - 25), (cx - 25, cy + 25), 4)
    txt = FONT_TINY.render("BLOCKED", True, (239, 83, 80))
    surf.blit(txt, (cx - txt.get_width() // 2, cy + 35))


def draw_coq(surf, x, y, label=True):
    pts = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        pts.append((x + int(10 * math.cos(angle)), y + int(10 * math.sin(angle))))
    pygame.draw.polygon(surf, COQ_ORANGE, pts)
    pygame.draw.polygon(surf, (255, 160, 50), pts, 1)
    # Small e- indicator inside
    pygame.draw.circle(surf, ELECTRON_COLOR, (x, y), 3)
    if label:
        txt = FONT_TINY.render("CoQ", True, COQ_ORANGE)
        surf.blit(txt, (x - txt.get_width() // 2, y - 18))


def draw_cytc(surf, x, y, label=True):
    pygame.draw.circle(surf, CYTC_BLUE_LIGHT, (int(x), int(y)), 9)
    pygame.draw.circle(surf, (100, 130, 200), (int(x), int(y)), 9, 1)
    # Small e- indicator
    pygame.draw.circle(surf, ELECTRON_COLOR, (int(x), int(y)), 3)
    if label:
        txt = FONT_TINY.render("Cyt c", True, CYTC_BLUE_LIGHT)
        surf.blit(txt, (int(x) - txt.get_width() // 2, int(y) - 20))


# ---------------------------------------------------------------------------
# Membrane drawing
# ---------------------------------------------------------------------------
def draw_membrane(surf):
    pygame.draw.rect(surf, MEMBRANE_COLOR,
                     (SIM_X, MEMBRANE_Y - MEMBRANE_H // 2, SIM_W, MEMBRANE_H))
    for x in range(SIM_X, WIDTH, 14):
        pygame.draw.circle(surf, MEMBRANE_EDGE, (x + 7, MEMBRANE_Y - MEMBRANE_H // 2), 5)
        pygame.draw.circle(surf, MEMBRANE_EDGE, (x + 7, MEMBRANE_Y + MEMBRANE_H // 2), 5)
    txt_ims = FONT_MD.render("Intermembrane Space (IMS)", True, LABEL_DIM)
    surf.blit(txt_ims, (SIM_X + 20, 20))
    txt_mat = FONT_MD.render("Mitochondrial Matrix", True, LABEL_DIM)
    surf.blit(txt_mat, (SIM_X + 20, HEIGHT - 40))


# ---------------------------------------------------------------------------
# Particle classes
# ---------------------------------------------------------------------------
class IMSProton:
    """A proton in the IMS. Drifts with Brownian motion, evenly distributed
       throughout the entire IMS space representing high [H+] concentration."""

    def __init__(self, x, y):
        # Spawn at random position across full IMS
        self.x = random.randint(SIM_X + 20, WIDTH - 20)
        self.y = random.randint(20, IMS_BOTTOM - 15)
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-0.8, 0.8)
        self.alive = True

    def update(self):
        # Pure Brownian motion - protons spread evenly throughout IMS
        self.x += self.vx
        self.y += self.vy

        # Bounce within IMS bounds - use FULL width and height
        if self.x < SIM_X + 10:
            self.x = SIM_X + 10
            self.vx = abs(self.vx)
        if self.x > WIDTH - 10:
            self.x = WIDTH - 10
            self.vx = -abs(self.vx)
        if self.y < 15:
            self.y = 15
            self.vy = abs(self.vy)
        if self.y > IMS_BOTTOM - 10:
            self.y = IMS_BOTTOM - 10
            self.vy = -abs(self.vy)

        # Random Brownian drift - strong enough to spread quickly
        self.vx += random.uniform(-0.165, 0.165)
        self.vy += random.uniform(-0.165, 0.165)

        # Damping
        self.vx *= 0.94
        self.vy *= 0.94
        self.vx = max(-1.1, min(1.1, self.vx))
        self.vy = max(-1.1, min(1.1, self.vy))

    def draw(self, surf):
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 4)


class PumpingProton:
    """A proton being actively pumped UP through a complex into IMS.
       Starts inside the complex body, exits from the top into IMS."""
    def __init__(self, start_x, start_y, target_y):
        self.x = start_x
        self.y = start_y
        self.target_y = target_y
        self.speed = 1.5 + random.random()
        self.done = False

    def update(self, speed):
        self.y -= self.speed * speed
        if self.y <= self.target_y:
            self.y = self.target_y
            self.done = True

    def draw(self, surf):
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 4)
        # Small upward arrow
        pygame.draw.line(surf, PROTON_COLOR, (int(self.x), int(self.y) - 6),
                         (int(self.x), int(self.y) - 10), 1)
        pygame.draw.line(surf, PROTON_COLOR, (int(self.x) - 3, int(self.y) - 8),
                         (int(self.x), int(self.y) - 10), 1)
        pygame.draw.line(surf, PROTON_COLOR, (int(self.x) + 3, int(self.y) - 8),
                         (int(self.x), int(self.y) - 10), 1)


class InfluxProton:
    """A proton flowing DOWN through CV (ATP synthase) from IMS into matrix.
       Starts at the top of CV (Fo channel in IMS) and exits bottom into matrix."""
    def __init__(self, cx):
        self.x = cx + random.uniform(-4, 4)
        self.y = MEMBRANE_Y - 40  # start at top of CV (Fo channel, IMS side)
        self.target_y = MATRIX_TOP + 60  # travel into matrix
        self.speed = 0.8 + random.random() * 0.4
        self.done = False

    def update(self, speed):
        self.y += self.speed * speed
        if self.y >= self.target_y:
            self.done = True

    def draw(self, surf):
        # Larger, brighter proton with clear downward arrow
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(surf, (150, 240, 255), (int(self.x), int(self.y)), 5, 1)
        # Downward arrow below
        ax, ay = int(self.x), int(self.y)
        pygame.draw.line(surf, PROTON_COLOR, (ax, ay + 6), (ax, ay + 14), 2)
        pygame.draw.line(surf, PROTON_COLOR, (ax - 4, ay + 10), (ax, ay + 14), 2)
        pygame.draw.line(surf, PROTON_COLOR, (ax + 4, ay + 10), (ax, ay + 14), 2)
        # "H+" label
        txt = FONT_TINY.render("H\u207a", True, PROTON_COLOR)
        surf.blit(txt, (ax + 7, ay - 6))


class LeakProton:
    """Proton leaking through membrane due to uncoupler (no ATP made)."""
    def __init__(self):
        self.x = random.randint(SIM_X + 60, WIDTH - 60)
        self.y = IMS_BOTTOM
        self.target_y = MATRIX_TOP + 20
        self.speed = 2.0 + random.random()
        self.done = False

    def update(self, speed):
        self.y += self.speed * speed
        if self.y >= self.target_y:
            self.done = True

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 152, 0), (int(self.x), int(self.y)), 3)


MATRIX_PROTON_CAP = 120

class MatrixProton:
    """A proton in the matrix. Drifts around, consumed when complexes pump H+ out."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.3, 0.3)
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        # Bounce within matrix bounds
        if self.x < SIM_X + 10:
            self.x = SIM_X + 10; self.vx = abs(self.vx)
        if self.x > WIDTH - 10:
            self.x = WIDTH - 10; self.vx = -abs(self.vx)
        if self.y < MATRIX_TOP + 10:
            self.y = MATRIX_TOP + 10; self.vy = abs(self.vy)
        if self.y > HEIGHT - 15:
            self.y = HEIGHT - 15; self.vy = -abs(self.vy)
        # Brownian drift
        self.vx += random.uniform(-0.05, 0.05)
        self.vy += random.uniform(-0.05, 0.05)
        self.vx *= 0.97
        self.vy *= 0.97
        self.vx = max(-0.5, min(0.5, self.vx))
        self.vy = max(-0.5, min(0.5, self.vy))

    def draw(self, surf):
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 3)


class WaterParticle:
    """H2O molecule produced at CIV when O2 + matrix H+ combine."""
    def __init__(self, x, y):
        self.x = x + random.uniform(-15, 15)
        self.y = y
        self.alpha = 220
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(0.3, 0.8)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha -= 1.5

    def draw(self, surf):
        if self.alpha <= 0:
            return
        a = int(max(0, self.alpha))
        # Blue water droplet
        drop_surf = pygame.Surface((20, 16), pygame.SRCALPHA)
        pygame.draw.circle(drop_surf, (80, 160, 255, a), (10, 10), 6)
        pygame.draw.polygon(drop_surf, (80, 160, 255, a), [(10, 2), (6, 8), (14, 8)])
        surf.blit(drop_surf, (int(self.x) - 10, int(self.y) - 8))
        txt = FONT_TINY.render("H\u2082O", True, (130, 190, 255))
        txt.set_alpha(a)
        surf.blit(txt, (int(self.x) + 8, int(self.y) - 6))


class CoQShuttle:
    """Ubiquinone carrying electrons LATERALLY within the membrane from CI/CII to CIII."""
    def __init__(self, start_x, end_x):
        self.x = start_x
        self.y = MEMBRANE_Y + random.uniform(-8, 8)
        self.end_x = end_x
        self.speed = 1.8
        self.alive = True
        self.arrived = False

    def update(self, speed):
        dx = self.end_x - self.x
        if abs(dx) < 5:
            self.alive = False
            self.arrived = True
        else:
            self.x += (dx / abs(dx)) * self.speed * speed

    def draw(self, surf):
        draw_coq(surf, int(self.x), int(self.y), label=False)


class CytCShuttle:
    """Cytochrome c carrying electrons along IMS (above membrane) from CIII to CIV."""
    def __init__(self, start_x, end_x):
        self.x = start_x
        self.y = IMS_BOTTOM - 15 + random.uniform(-3, 3)
        self.end_x = end_x
        self.speed = 2.0
        self.alive = True
        self.arrived = False

    def update(self, speed):
        dx = self.end_x - self.x
        if abs(dx) < 5:
            self.alive = False
            self.arrived = True
        else:
            self.x += (dx / abs(dx)) * self.speed * speed

    def draw(self, surf):
        draw_cytc(surf, self.x, self.y, label=False)


class ATPParticle:
    """Two-phase animation:
       Phase 1 (approach): ADP + Pi (2 phosphates + free Pi) rises toward CV.
       Phase 2 (convert):  Brief flash at CV as 3rd phosphate attaches.
       Phase 3 (release):  ATP (3 phosphates) drifts away into matrix.
    """
    P_COLOR = (0, 200, 80)
    P_OUTLINE = (0, 140, 50)
    P_NEW_COLOR = (100, 255, 100)  # brighter green for the newly added 3rd P
    ADENOSINE_COLOR = (200, 80, 80)

    def __init__(self, cv_x, matrix_top):
        # Start well below CV in the matrix
        self.x = cv_x - 20 + random.uniform(-10, 10)
        self.y = matrix_top + 160 + random.uniform(0, 30)
        # Target: the F1 head of CV
        self.target_y = matrix_top + 25
        self.cv_x = cv_x
        self.phase = "approach"
        self.convert_timer = 0
        self.alpha = 255
        # Release direction: clearly AWAY from CV into the matrix (always leftward + down)
        self.release_vx = random.uniform(-1.5, -0.6)
        self.release_vy = random.uniform(0.8, 1.2)
        self.age = 0  # for the new phosphate highlight

    def update(self):
        if self.phase == "approach":
            # ADP + Pi moves toward CV - fairly quick so they don't pile up
            dy = self.target_y - self.y
            dx = self.cv_x - self.x
            speed = 0.06
            self.y += dy * speed
            self.x += dx * speed
            if abs(dy) < 4:
                self.phase = "convert"
                self.convert_timer = 35
                self.x = self.cv_x
                self.y = self.target_y
        elif self.phase == "convert":
            self.convert_timer -= 1
            if self.convert_timer <= 0:
                self.phase = "release"
                self.age = 0
                # Kick it away from CV immediately so 3P is clearly leaving
                self.x += self.release_vx * 15
                self.y += self.release_vy * 10
        elif self.phase == "release":
            self.x += self.release_vx
            self.y += self.release_vy
            self.alpha -= 1.2
            self.age += 1
            if self.alpha <= 0:
                self.alpha = 0

    def _draw_molecule(self, surf, x, y, phosphate_count, alpha_val, highlight_3rd=False):
        """Draw adenosine + phosphate chain."""
        a = int(max(0, min(255, alpha_val)))
        ix, iy = int(x), int(y)

        # Adenosine base
        base_surf = pygame.Surface((16, 12), pygame.SRCALPHA)
        pygame.draw.rect(base_surf, (*self.ADENOSINE_COLOR, a), (0, 0, 16, 12), border_radius=3)
        # "A" label on base
        a_txt = FONT_TINY.render("A", True, (255, 255, 255))
        a_txt.set_alpha(a)
        base_surf.blit(a_txt, (4, 0))
        surf.blit(base_surf, (ix - 8, iy - 6))

        # Phosphate circles
        for i in range(phosphate_count):
            px = ix + 14 + i * 14
            is_new = (i == 2 and highlight_3rd)
            color = self.P_NEW_COLOR if is_new else self.P_COLOR
            radius = 7 if is_new else 6

            circ_surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(circ_surf, (*color, a), (radius + 1, radius + 1), radius)
            pygame.draw.circle(circ_surf, (*self.P_OUTLINE, a), (radius + 1, radius + 1), radius, 1)
            surf.blit(circ_surf, (px - radius - 1, iy - radius - 1))

            p_txt = FONT_TINY.render("P", True, (255, 255, 255))
            p_txt.set_alpha(a)
            surf.blit(p_txt, (px - 4, iy - 6))

            # Bond line to previous
            if i > 0:
                lx = ix + 14 + (i - 1) * 14 + 7
                line_surf = pygame.Surface((7, 2), pygame.SRCALPHA)
                pygame.draw.line(line_surf, (*self.P_OUTLINE, a), (0, 1), (7, 1), 2)
                surf.blit(line_surf, (lx, iy - 1))

    def draw(self, surf):
        if self.alpha <= 0:
            return

        if self.phase == "approach":
            # ADP (adenosine + 2 phosphates ONLY)
            self._draw_molecule(surf, self.x, self.y, 2, self.alpha)

            # Free Pi drawn WELL SEPARATED - below and to the right, not touching the chain
            pi_x = int(self.x) + 16
            pi_y = int(self.y) + 18
            circ_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(circ_surf, (255, 180, 0, int(self.alpha)), (7, 7), 5)
            pygame.draw.circle(circ_surf, (200, 140, 0, int(self.alpha)), (7, 7), 5, 1)
            surf.blit(circ_surf, (pi_x - 7, pi_y - 7))
            pi_txt = FONT_TINY.render("Pi", True, (255, 255, 255))
            pi_txt.set_alpha(int(self.alpha))
            surf.blit(pi_txt, (pi_x - 6, pi_y - 7))

            # Label above
            lbl = FONT_SM.render("ADP + Pi", True, (200, 200, 255))
            lbl.set_alpha(int(self.alpha))
            surf.blit(lbl, (int(self.x) - 10, int(self.y) - 22))

        elif self.phase == "convert":
            # Conversion flash: 3rd phosphate appearing, pulsing highlight
            pulse = 0.5 + 0.5 * math.sin(self.convert_timer * 0.4)
            flash_a = int(180 + 75 * pulse)
            self._draw_molecule(surf, self.x, self.y, 3, flash_a, highlight_3rd=True)

            lbl = FONT_LG.render("ATP!", True, ATP_COLOR)
            lbl.set_alpha(flash_a)
            surf.blit(lbl, (int(self.x) - 10, int(self.y) - 28))

        elif self.phase == "release":
            # ATP (3 phosphates) drifting into matrix
            highlight = self.age < 40  # new 3rd P stays highlighted briefly
            self._draw_molecule(surf, self.x, self.y, 3, self.alpha, highlight_3rd=highlight)

            lbl = FONT_TINY.render("ATP", True, ATP_COLOR)
            lbl.set_alpha(int(max(0, self.alpha)))
            surf.blit(lbl, (int(self.x) - 5, int(self.y) - 18))


class ROSParticle:
    def __init__(self, x, y):
        self.x = x + random.uniform(-20, 20)
        self.y = y + random.uniform(-20, 20)
        self.alpha = 200
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha -= 3

    def draw(self, surf):
        if self.alpha <= 0:
            return
        s = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(s, (*ROS_COLOR, int(max(0, self.alpha))), (7, 7), 7)
        surf.blit(s, (int(self.x) - 7, int(self.y) - 7))
        txt = FONT_TINY.render("O\u2082\u207b", True, ROS_COLOR)
        txt.set_alpha(int(max(0, self.alpha)))
        surf.blit(txt, (int(self.x) + 8, int(self.y) - 6))


# ---------------------------------------------------------------------------
# Simulation state
# ---------------------------------------------------------------------------
class SimState:
    def __init__(self):
        self.reset()

    def reset(self):
        # Particle pools
        self.ims_protons = []       # protons floating in IMS (the gradient!)
        # Seed matrix with starting protons (from ongoing metabolism)
        self.matrix_protons = []
        for _ in range(50):
            self.matrix_protons.append(MatrixProton(
                random.randint(SIM_X + 40, WIDTH - 40),
                random.randint(MATRIX_TOP + 20, HEIGHT - 30)))
        self.pumping_protons = []   # protons being pumped upward through complexes
        self.influx_protons = []    # protons flowing down through CV
        self.leak_protons = []      # uncoupler leak protons
        self.coq_shuttles = []
        self.cytc_shuttles = []
        self.atp_particles = []
        self.ros_particles = []
        self.water_particles = []

        # Complex activation flash timers (frames remaining)
        self.complex_active = {"CI": 0, "CII": 0, "CIII": 0, "CIV": 0, "CV": 0}

        self.atp_count = 0
        self.atp_rate = 0.0
        self.atp_history = []

        self.cv_rotation = 0.0
        self.frame = 0
        self.flux = 1.5
        self.paused = False

        self.blocked = {"CI": False, "CII": False, "CIII": False, "CIV": False, "CV": False}
        self.partial_block = {"CI": False}
        self.uncoupled = False
        self.uncoupler_strength = 0.0
        self.transport_blocked = False
        self.ros_generating = {"CI": False}

        self.active_chemicals = []

        self.info_panel = None
        self.info_panel_rect = None
        self.sidebar_scroll = 0
        self.sidebar_max_scroll = 0
        self.dragging_chem = None
        self.drag_pos = (0, 0)
        self.hovered_complex = None

        # Gradient counter for HUD
        self.gradient_display = 0

    def apply_chemical(self, chem):
        if chem["id"] in [c["id"] for c in self.active_chemicals]:
            return
        self.active_chemicals.append(chem)
        self._apply_effect(chem)

    def remove_chemical(self, chem_id):
        self.active_chemicals = [c for c in self.active_chemicals if c["id"] != chem_id]
        self.blocked = {"CI": False, "CII": False, "CIII": False, "CIV": False, "CV": False}
        self.partial_block = {"CI": False}
        self.uncoupled = False
        self.uncoupler_strength = 0.0
        self.transport_blocked = False
        self.ros_generating = {"CI": False}
        for c in self.active_chemicals:
            self._apply_effect(c)

    def _apply_effect(self, chem):
        target = chem["target"]
        effect = chem["effect"]
        if effect == "block" and target in self.blocked:
            self.blocked[target] = True
        elif effect == "partial_block" and target == "CI":
            self.partial_block["CI"] = True
        elif effect == "uncouple":
            self.uncoupled = True
            self.uncoupler_strength = min(1.0, self.uncoupler_strength + 0.5)
        elif effect == "transport_block":
            self.transport_blocked = True
        elif effect == "ros_generation":
            self.ros_generating["CI"] = True

    def effective_ci_rate(self):
        if self.blocked["CI"]:
            return 0.0
        if self.partial_block["CI"]:
            return 0.3
        return 1.0

    def effective_cii_rate(self):
        return 0.0 if self.blocked["CII"] else 1.0


sim = SimState()


# ---------------------------------------------------------------------------
# Main simulation update
# ---------------------------------------------------------------------------
def sim_update():
    flux = sim.flux
    f = sim.frame

    ci_rate = sim.effective_ci_rate()
    cii_rate = sim.effective_cii_rate()
    ciii_ok = not sim.blocked["CIII"]
    civ_ok = not sim.blocked["CIV"]
    downstream_ok = ciii_ok and civ_ok

    # --- Step 1: NADH donates electrons to Complex I ---
    # CI accepts electrons, pumps 4H+, passes e- to CoQ
    spawn_nadh = max(1, int(55 / flux))
    if ci_rate > 0 and downstream_ok and f % spawn_nadh == 0:
        if ci_rate < 1.0 and random.random() > ci_rate:
            pass
        else:
            # CI activates: pump protons, launch CoQ shuttle
            sim.complex_active["CI"] = 20
            _pump_protons("CI", 4)
            sim.coq_shuttles.append(CoQShuttle(CX["CI"] + 40, CX["CIII"]))

    # --- Step 2: FADH2 donates electrons to Complex II ---
    # CII accepts electrons (no pump), passes e- to CoQ
    spawn_fadh2 = max(1, int(80 / flux))
    if cii_rate > 0 and downstream_ok and f % spawn_fadh2 == 0:
        sim.complex_active["CII"] = 20
        sim.coq_shuttles.append(CoQShuttle(CX["CII"] + 35, CX["CIII"]))

    # --- Step 3: CoQ shuttles carry e- laterally to CIII ---
    for c in sim.coq_shuttles:
        c.update(flux)
        if c.arrived:
            # CIII activates: pump 4H+, launch Cyt c
            sim.complex_active["CIII"] = 20
            if ciii_ok:
                _pump_protons("CIII", 4)
                sim.cytc_shuttles.append(CytCShuttle(CX["CIII"], CX["CIV"]))
    sim.coq_shuttles = [c for c in sim.coq_shuttles if c.alive]

    # --- Step 4: Cyt c carries e- along IMS to CIV ---
    for c in sim.cytc_shuttles:
        c.update(flux)
        if c.arrived:
            # CIV activates: pump 2H+ to IMS, AND consume 2 matrix H+ to form H2O
            sim.complex_active["CIV"] = 20
            if civ_ok:
                _pump_protons("CIV", 2)
                # CIV also consumes 2 matrix H+ (combined with O2 to form water)
                _consume_matrix_protons_for_water("CIV", 2)
    sim.cytc_shuttles = [c for c in sim.cytc_shuttles if c.alive]

    # --- Step 5: Pumping protons travel upward into IMS ---
    for p in sim.pumping_protons:
        p.update(flux)
    # Convert finished pumping protons into persistent IMS protons
    for p in sim.pumping_protons:
        if p.done:
            if len(sim.ims_protons) < IMS_PROTON_CAP:
                sim.ims_protons.append(IMSProton(p.x, p.target_y))

    # --- Redistribute IMS protons so they don't cluster ---
    # Each frame, nudge a few protons toward empty regions
    if len(sim.ims_protons) > 10 and f % 5 == 0:
        # Pick a random proton and teleport it to a random spot if it's in a crowded area
        idx = random.randint(0, len(sim.ims_protons) - 1)
        p = sim.ims_protons[idx]
        # Count neighbors within 80px
        neighbors = sum(1 for other in sim.ims_protons
                        if abs(other.x - p.x) < 80 and abs(other.y - p.y) < 80)
        if neighbors > 8:  # too crowded, relocate
            p.x = random.randint(SIM_X + 20, WIDTH - 20)
            p.y = random.randint(20, IMS_BOTTOM - 15)
    sim.pumping_protons = [p for p in sim.pumping_protons if not p.done]

    # --- Step 6: IMS protons drift around (visible gradient!) ---
    for p in sim.ims_protons:
        p.update()
    sim.gradient_display = len(sim.ims_protons)

    # --- Step 6b: Matrix protons drift around ---
    for p in sim.matrix_protons:
        p.update()

    # --- Step 7: CV draws protons from IMS pool to make ATP ---
    cv_ok = not sim.blocked["CV"] and not sim.transport_blocked
    effective_gradient = 1.0
    if sim.uncoupled:
        effective_gradient = max(0.1, 1.0 - sim.uncoupler_strength)

    cv_interval = max(1, int(30 / (flux * effective_gradient)))
    if cv_ok and len(sim.ims_protons) > 0 and f % cv_interval == 0:
        # Consume a proton from IMS
        # Pick one near CV preferentially
        best_idx = 0
        best_dist = 99999
        for i, p in enumerate(sim.ims_protons):
            d = abs(p.x - CX["CV"])
            if d < best_dist:
                best_dist = d
                best_idx = i
        sim.ims_protons.pop(best_idx)
        sim.influx_protons.append(InfluxProton(CX["CV"]))
        sim.complex_active["CV"] = 10

    # Update influx protons - when they arrive in matrix, add to matrix pool
    atp_this_frame = 0
    for p in sim.influx_protons:
        p.update(flux)
        if p.done:
            # Proton enters the matrix pool
            if len(sim.matrix_protons) < MATRIX_PROTON_CAP:
                sim.matrix_protons.append(MatrixProton(
                    CX["CV"] + random.uniform(-30, 30),
                    MATRIX_TOP + 20 + random.uniform(0, 40)))
            # ~4 H+ per ATP, so 25% chance per proton
            if random.random() < 0.25:
                sim.atp_particles.append(ATPParticle(CX["CV"], MATRIX_TOP))
                atp_this_frame += 1
    sim.influx_protons = [p for p in sim.influx_protons if not p.done]

    sim.atp_count += atp_this_frame
    sim.atp_history.append(atp_this_frame)
    if len(sim.atp_history) > 60:
        sim.atp_history.pop(0)
    sim.atp_rate = sum(sim.atp_history)

    # --- Uncoupler leak: protons leak from IMS through membrane (no ATP) ---
    if sim.uncoupled and len(sim.ims_protons) > 0 and f % max(1, int(8 / flux)) == 0:
        # Remove a random IMS proton and create a leak visual
        idx = random.randint(0, len(sim.ims_protons) - 1)
        sim.ims_protons.pop(idx)
        sim.leak_protons.append(LeakProton())

    for p in sim.leak_protons:
        p.update(flux)
        if p.done and len(sim.matrix_protons) < MATRIX_PROTON_CAP:
            sim.matrix_protons.append(MatrixProton(p.x, MATRIX_TOP + 20 + random.uniform(0, 30)))
    sim.leak_protons = [p for p in sim.leak_protons if not p.done]

    # --- ROS ---
    if sim.ros_generating.get("CI", False) and f % 30 == 0:
        sim.ros_particles.append(ROSParticle(CX["CI"], MEMBRANE_Y))
    if sim.blocked["CIII"] and f % 25 == 0:
        sim.ros_particles.append(ROSParticle(CX["CIII"], MEMBRANE_Y - 30))

    for r in sim.ros_particles:
        r.update()
    sim.ros_particles = [r for r in sim.ros_particles if r.alpha > 0]

    # --- Water particles from CIV ---
    for w in sim.water_particles:
        w.update()
    sim.water_particles = [w for w in sim.water_particles if w.alpha > 0]

    # --- ATP particles ---
    for a in sim.atp_particles:
        a.update()
    sim.atp_particles = [a for a in sim.atp_particles if a.alpha > 0]

    # --- CV rotation ---
    rotation_speed = 0.05 * flux * effective_gradient
    if sim.blocked["CV"] or sim.transport_blocked:
        rotation_speed = 0
    sim.cv_rotation += rotation_speed

    # --- Metabolic H+ generation in matrix ---
    # TCA cycle, NADH/FADH2 reactions, and other metabolism constantly produce H+ in matrix
    metabolic_interval = max(1, int(5 / flux))
    if f % metabolic_interval == 0 and len(sim.matrix_protons) < MATRIX_PROTON_CAP:
        sim.matrix_protons.append(MatrixProton(
            random.randint(SIM_X + 40, WIDTH - 100),
            random.randint(MATRIX_TOP + 30, HEIGHT - 30)))

    # Decay complex active timers
    for k in sim.complex_active:
        if sim.complex_active[k] > 0:
            sim.complex_active[k] -= 1

    sim.frame += 1


def _pump_protons(complex_key, count):
    """Consume protons from matrix pool and pump them UP THROUGH the complex into IMS.
       Protons always start inside the complex body and exit from the top."""
    cx = CX[complex_key]
    for _ in range(count):
        # Consume a matrix proton if available
        if sim.matrix_protons:
            best_idx = 0
            best_dist = 99999
            for i, mp in enumerate(sim.matrix_protons):
                d = abs(mp.x - cx)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            sim.matrix_protons.pop(best_idx)

        # Proton starts INSIDE the complex (bottom half, near membrane)
        start_x = cx + random.uniform(-10, 10)
        start_y = MEMBRANE_Y + random.uniform(5, 20)  # inside complex, below center

        # Ends up in IMS at varied heights
        target_y = 30 + random.random() * (IMS_BOTTOM - 60)

        p = PumpingProton(start_x, start_y, target_y)
        sim.pumping_protons.append(p)


def _consume_matrix_protons_for_water(complex_key, count):
    """CIV consumes matrix H+ to combine with O2, producing H2O."""
    cx = CX[complex_key]
    for _ in range(count):
        if sim.matrix_protons:
            best_idx = 0
            best_dist = 99999
            for i, mp in enumerate(sim.matrix_protons):
                d = abs(mp.x - cx)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            sim.matrix_protons.pop(best_idx)
    # Produce one H2O molecule (2H+ + 1/2 O2 -> H2O)
    sim.water_particles.append(WaterParticle(cx, MATRIX_TOP + 40))


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
def draw_all(mx, my):
    screen.fill(BG_COLOR)

    # Zone backgrounds
    pygame.draw.rect(screen, IMS_COLOR, (SIM_X, 0, SIM_W, IMS_BOTTOM))
    pygame.draw.rect(screen, MATRIX_COLOR, (SIM_X, MATRIX_TOP, SIM_W, HEIGHT - MATRIX_TOP))

    # Membrane
    draw_membrane(screen)

    # Static carrier pathway labels
    # CoQ path (horizontal arrow in membrane between CI/CII and CIII)
    coq_start = CX["CI"] + 50
    coq_end = CX["CIII"] - 35
    coq_mid = (coq_start + coq_end) // 2
    pygame.draw.line(screen, COQ_ORANGE, (coq_start, MEMBRANE_Y), (coq_end, MEMBRANE_Y), 1)
    # Arrowhead
    pygame.draw.polygon(screen, COQ_ORANGE,
                        [(coq_end, MEMBRANE_Y), (coq_end - 8, MEMBRANE_Y - 4), (coq_end - 8, MEMBRANE_Y + 4)])
    txt = FONT_TINY.render("CoQ (in membrane)", True, COQ_ORANGE)
    screen.blit(txt, (coq_mid - txt.get_width() // 2, MEMBRANE_Y + 12))

    # Also from CII
    coq2_start = CX["CII"] + 35
    pygame.draw.line(screen, COQ_ORANGE, (coq2_start, MEMBRANE_Y + 5), (coq_end, MEMBRANE_Y + 5), 1)

    # Cyt c path (horizontal in IMS between CIII and CIV)
    cytc_start = CX["CIII"] + 35
    cytc_end = CX["CIV"] - 30
    cytc_mid = (cytc_start + cytc_end) // 2
    cytc_y = IMS_BOTTOM - 15
    pygame.draw.line(screen, CYTC_BLUE_LIGHT, (cytc_start, cytc_y), (cytc_end, cytc_y), 1)
    pygame.draw.polygon(screen, CYTC_BLUE_LIGHT,
                        [(cytc_end, cytc_y), (cytc_end - 8, cytc_y - 4), (cytc_end - 8, cytc_y + 4)])
    txt = FONT_TINY.render("Cyt c (in IMS)", True, CYTC_BLUE_LIGHT)
    screen.blit(txt, (cytc_mid - txt.get_width() // 2, cytc_y - 18))

    # Mobile carriers (CoQ shuttles move within membrane, Cyt c above)
    for c in sim.coq_shuttles:
        c.draw(screen)
    for c in sim.cytc_shuttles:
        c.draw(screen)

    # Complexes
    hovered = get_complex_at(mx, my)
    sim.hovered_complex = hovered

    draw_complex_I(screen, CX["CI"], MEMBRANE_Y,
                   blocked=sim.blocked["CI"], highlight=(hovered == "CI"),
                   active=sim.complex_active["CI"] > 0)
    draw_complex_II(screen, CX["CII"], MEMBRANE_Y,
                    blocked=sim.blocked["CII"], highlight=(hovered == "CII"),
                    active=sim.complex_active["CII"] > 0)
    draw_complex_III(screen, CX["CIII"], MEMBRANE_Y,
                     blocked=sim.blocked["CIII"], highlight=(hovered == "CIII"),
                     active=sim.complex_active["CIII"] > 0)
    draw_complex_IV(screen, CX["CIV"], MEMBRANE_Y,
                    blocked=sim.blocked["CIV"], highlight=(hovered == "CIV"),
                    active=sim.complex_active["CIV"] > 0)
    draw_complex_V(screen, CX["CV"], MEMBRANE_Y,
                   rotation=sim.cv_rotation,
                   blocked=sim.blocked["CV"] or sim.transport_blocked,
                   highlight=(hovered == "CV"))

    # Partial block indicator
    if sim.partial_block.get("CI"):
        txt = FONT_TINY.render("PARTIAL INHIBITION", True, (255, 200, 50))
        screen.blit(txt, (CX["CI"] - txt.get_width() // 2, MEMBRANE_Y + 78))

    # Uncoupler visual
    if sim.uncoupled:
        for i in range(6):
            lx = SIM_X + 60 + i * (SIM_W - 120) // 6
            s = pygame.Surface((24, MEMBRANE_H + 6), pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 152, 0, 50), (0, 0, 24, MEMBRANE_H + 6), border_radius=4)
            screen.blit(s, (lx, MEMBRANE_Y - MEMBRANE_H // 2 - 3))
        utxt = FONT_SM.render("UNCOUPLED \u2014 H\u207a leaking through membrane!", True, (255, 152, 0))
        screen.blit(utxt, (SIM_X + SIM_W // 2 - utxt.get_width() // 2, MATRIX_TOP + 30))

    # --- Subtle flow indicator near CV ---
    # Just a small downward arrow above CV showing where protons enter
    if sim.gradient_display > 5 and not (sim.blocked["CV"] or sim.transport_blocked):
        arr_surf = pygame.Surface((30, 20), pygame.SRCALPHA)
        pygame.draw.polygon(arr_surf, (0, 200, 240, 80),
                            [(15, 20), (3, 6), (27, 6)])
        screen.blit(arr_surf, (CX["CV"] - 15, IMS_BOTTOM - 25))
        txt = FONT_TINY.render("H\u207a flow", True, (0, 200, 240))
        txt.set_alpha(100)
        screen.blit(txt, (CX["CV"] - txt.get_width() // 2, IMS_BOTTOM - 40))

    # --- Draw all protons ---
    # Matrix protons (source pool for pumping)
    for p in sim.matrix_protons:
        p.draw(screen)

    # IMS protons (the accumulated gradient!)
    for p in sim.ims_protons:
        p.draw(screen)

    # Pumping protons (moving upward through complexes)
    for p in sim.pumping_protons:
        p.draw(screen)

    # Influx protons (moving down through CV)
    for p in sim.influx_protons:
        p.draw(screen)

    # Leak protons
    for p in sim.leak_protons:
        p.draw(screen)

    # ATP particles
    for a in sim.atp_particles:
        a.draw(screen)

    # ROS particles
    for r in sim.ros_particles:
        r.draw(screen)

    # Water particles from CIV
    for w in sim.water_particles:
        w.draw(screen)

    # Gradient indicator text in IMS
    if sim.gradient_display > 0:
        g_txt = FONT_SM.render(f"H\u207a gradient: {sim.gradient_display} protons in IMS", True, PROTON_COLOR)
        screen.blit(g_txt, (WIDTH - g_txt.get_width() - 20, IMS_BOTTOM - 30))

    # Matrix proton pool label
    if len(sim.matrix_protons) > 0:
        m_txt = FONT_SM.render(f"Matrix H\u207a pool: {len(sim.matrix_protons)} (source for pumping)", True, (100, 200, 220))
        screen.blit(m_txt, (SIM_X + 20, MATRIX_TOP + 15))

    # Sidebar
    ui = draw_sidebar(screen, mx, my)

    # HUD
    draw_hud(screen)

    # Tooltip
    if hovered and sim.info_panel is None and mx > SIDEBAR_W:
        info = COMPLEX_INFO.get(hovered, {})
        tip = FONT_SM.render(f"Click for details: {info.get('name', hovered)}", True, ACCENT)
        tip_bg = pygame.Surface((tip.get_width() + 16, tip.get_height() + 8), pygame.SRCALPHA)
        tip_bg.fill((0, 0, 0, 180))
        screen.blit(tip_bg, (mx + 15, my - 25))
        screen.blit(tip, (mx + 23, my - 21))

    # Dragging chemical
    if sim.dragging_chem:
        dx, dy = sim.drag_pos
        s = pygame.Surface((180, 36), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 60, 80, 200), (0, 0, 180, 36), border_radius=8)
        ntxt = FONT_TITLE.render(sim.dragging_chem["name"], True, ACCENT)
        s.blit(ntxt, (8, 8))
        screen.blit(s, (dx - 90, dy - 18))

    # Info panel (on top)
    draw_info_panel(screen)

    return ui


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def draw_sidebar(surf, mx, my):
    pygame.draw.rect(surf, SIDEBAR_BG, (0, 0, SIDEBAR_W, HEIGHT))
    pygame.draw.line(surf, (60, 60, 80), (SIDEBAR_W - 1, 0), (SIDEBAR_W - 1, HEIGHT))

    title = FONT_XL.render("Chemicals", True, ACCENT)
    surf.blit(title, (15, 12))
    subtitle = FONT_TINY.render("Drag onto simulation or click to learn more", True, LABEL_DIM)
    surf.blit(subtitle, (15, 42))
    pygame.draw.line(surf, (60, 60, 80), (10, 60), (SIDEBAR_W - 10, 60))

    list_y_start = 70
    item_h = 52
    visible_h = HEIGHT - list_y_start - 100
    total_h = len(CHEMICALS) * item_h
    sim.sidebar_max_scroll = max(0, total_h - visible_h)

    clip_rect = pygame.Rect(0, list_y_start, SIDEBAR_W, visible_h)
    surf.set_clip(clip_rect)

    for i, chem in enumerate(CHEMICALS):
        iy = list_y_start + i * item_h - sim.sidebar_scroll
        if iy + item_h < list_y_start or iy > list_y_start + visible_h:
            continue

        item_rect = pygame.Rect(5, iy, SIDEBAR_W - 10, item_h - 4)
        is_active = chem["id"] in [c["id"] for c in sim.active_chemicals]
        is_hovered = item_rect.collidepoint(mx, my)

        if is_active:
            draw_rounded_rect(surf, (40, 80, 40), item_rect, 6)
            pygame.draw.rect(surf, (80, 180, 80), item_rect, 1, border_radius=6)
        elif is_hovered:
            draw_rounded_rect(surf, SIDEBAR_HIGHLIGHT, item_rect, 6)

        cat_color = (150, 150, 150)
        for cat in CHEM_DB["categories"]:
            if cat["id"] == chem["category"]:
                cat_color = tuple(cat["color"])
                break
        pygame.draw.circle(surf, cat_color, (20, iy + item_h // 2 - 2), 6)

        name_txt = FONT_TITLE.render(chem["name"], True, TEXT_COLOR)
        surf.blit(name_txt, (32, iy + 5))
        cat_txt = FONT_TINY.render(chem["category"], True, LABEL_DIM)
        surf.blit(cat_txt, (32, iy + 24))

        if is_active:
            act_txt = FONT_TINY.render("[ACTIVE - click to remove]", True, (100, 220, 100))
            surf.blit(act_txt, (32, iy + 36))

    surf.set_clip(None)

    if sim.sidebar_scroll > 0:
        pygame.draw.polygon(surf, LABEL_DIM, [(SIDEBAR_W // 2 - 8, list_y_start + 5),
                                               (SIDEBAR_W // 2 + 8, list_y_start + 5),
                                               (SIDEBAR_W // 2, list_y_start - 2)])
    if sim.sidebar_scroll < sim.sidebar_max_scroll:
        by = list_y_start + visible_h - 5
        pygame.draw.polygon(surf, LABEL_DIM, [(SIDEBAR_W // 2 - 8, by - 5),
                                               (SIDEBAR_W // 2 + 8, by - 5),
                                               (SIDEBAR_W // 2, by + 2)])

    btn_y = HEIGHT - 90
    pause_rect = pygame.Rect(10, btn_y, 80, 32)
    pause_hover = pause_rect.collidepoint(mx, my)
    draw_rounded_rect(surf, BUTTON_HOVER if pause_hover else BUTTON_COLOR, pause_rect, 6)
    ptxt = FONT_MD.render("Play" if sim.paused else "Pause", True, TEXT_COLOR)
    surf.blit(ptxt, (pause_rect.x + (pause_rect.w - ptxt.get_width()) // 2, btn_y + 6))

    step_rect = pygame.Rect(100, btn_y, 70, 32)
    step_hover = step_rect.collidepoint(mx, my)
    draw_rounded_rect(surf, BUTTON_HOVER if step_hover else BUTTON_COLOR, step_rect, 6)
    stxt = FONT_MD.render("Step", True, TEXT_COLOR)
    surf.blit(stxt, (step_rect.x + (step_rect.w - stxt.get_width()) // 2, btn_y + 6))

    reset_rect = pygame.Rect(180, btn_y, 80, 32)
    reset_hover = reset_rect.collidepoint(mx, my)
    draw_rounded_rect(surf, BUTTON_HOVER if reset_hover else BUTTON_COLOR, reset_rect, 6)
    rtxt = FONT_MD.render("Reset", True, TEXT_COLOR)
    surf.blit(rtxt, (reset_rect.x + (reset_rect.w - rtxt.get_width()) // 2, btn_y + 6))

    slider_y = btn_y + 42
    stxt = FONT_SM.render(f"Metabolic Flux: {sim.flux:.1f}x", True, LABEL_DIM)
    surf.blit(stxt, (10, slider_y))
    slider_rect = pygame.Rect(10, slider_y + 18, SIDEBAR_W - 20, 12)
    pygame.draw.rect(surf, (60, 60, 80), slider_rect, border_radius=6)
    knob_x = slider_rect.x + int((sim.flux - 0.5) / 2.5 * slider_rect.w)
    pygame.draw.circle(surf, ACCENT, (knob_x, slider_rect.y + 6), 8)

    return {
        "pause": pause_rect, "step": step_rect, "reset": reset_rect,
        "slider": slider_rect, "list_y_start": list_y_start,
        "item_h": item_h, "visible_h": visible_h,
    }


# ---------------------------------------------------------------------------
# Info panel
# ---------------------------------------------------------------------------
def draw_info_panel(surf):
    if sim.info_panel is None:
        return

    pw, ph = 450, 380
    px = (WIDTH - pw) // 2
    py = (HEIGHT - ph) // 2
    sim.info_panel_rect = pygame.Rect(px, py, pw, ph)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surf.blit(overlay, (0, 0))

    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    pygame.draw.rect(panel, (30, 30, 45, 240), (0, 0, pw, ph), border_radius=12)
    pygame.draw.rect(panel, ACCENT, (0, 0, pw, ph), 1, border_radius=12)

    info = sim.info_panel
    y = 15

    title = FONT_XL.render(info.get("name", ""), True, ACCENT)
    panel.blit(title, (15, y)); y += 35

    cat = FONT_MD.render(info.get("category", ""), True, LABEL_DIM)
    panel.blit(cat, (15, y)); y += 25

    target_txt = FONT_MD.render(f"Target: {info.get('target', 'N/A')}", True, TEXT_COLOR)
    panel.blit(target_txt, (15, y)); y += 25

    if "atp_reduction_pct" in info:
        atp_txt = FONT_MD.render(f"ATP Reduction: ~{info['atp_reduction_pct']}%", True, (239, 83, 80))
        panel.blit(atp_txt, (15, y)); y += 25

    pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 10

    for line in wrap_text(info.get("description", ""), FONT_SM, pw - 30):
        if y > ph - 70:
            break
        panel.blit(FONT_SM.render(line, True, TEXT_COLOR), (15, y)); y += 18

    y += 5
    if "clinical_notes" in info and y < ph - 50:
        pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 8
        panel.blit(FONT_TITLE.render("Clinical Notes:", True, (100, 200, 255)), (15, y)); y += 20
        for line in wrap_text(info["clinical_notes"], FONT_SM, pw - 30):
            if y > ph - 25:
                break
            panel.blit(FONT_SM.render(line, True, (180, 200, 220)), (15, y)); y += 17

    close_txt = FONT_SM.render("Click anywhere outside to close  |  ESC", True, LABEL_DIM)
    panel.blit(close_txt, (pw // 2 - close_txt.get_width() // 2, ph - 22))
    surf.blit(panel, (px, py))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def draw_hud(surf):
    hud_rect = pygame.Rect(WIDTH - 230, 10, 220, 90)
    draw_rounded_rect(surf, (0, 0, 0), hud_rect, 8, alpha=180)

    surf.blit(FONT_LG.render(f"ATP: {sim.atp_count}", True, ATP_COLOR), (WIDTH - 220, 15))
    surf.blit(FONT_SM.render(f"Rate: {sim.atp_rate:.1f} ATP/s", True, LABEL_DIM), (WIDTH - 220, 38))
    surf.blit(FONT_SM.render(f"H\u207a in IMS: {sim.gradient_display}", True, PROTON_COLOR), (WIDTH - 220, 55))
    surf.blit(FONT_SM.render(f"H\u207a in Matrix: {len(sim.matrix_protons)}", True, (100, 200, 220)), (WIDTH - 220, 70))

    if sim.active_chemicals:
        acy = 110
        surf.blit(FONT_TITLE.render("Active Effects:", True, (255, 150, 150)), (WIDTH - 220, acy))
        acy += 20
        for chem in sim.active_chemicals:
            surf.blit(FONT_SM.render(f"\u2022 {chem['name']}", True, (255, 180, 180)), (WIDTH - 215, acy))
            acy += 17

    # Legend
    leg_y = HEIGHT - 90
    leg_x = WIDTH - 210
    draw_rounded_rect(surf, (0, 0, 0), (leg_x - 10, leg_y - 5, 210, 85), 6, alpha=150)

    pygame.draw.circle(surf, PROTON_COLOR, (leg_x, leg_y + 8), 4)
    surf.blit(FONT_SM.render("Proton (H\u207a)", True, TEXT_COLOR), (leg_x + 12, leg_y))

    draw_coq(surf, leg_x, leg_y + 28, label=False)
    surf.blit(FONT_SM.render("Ubiquinone (CoQ) + e\u207b", True, TEXT_COLOR), (leg_x + 14, leg_y + 20))

    draw_cytc(surf, leg_x, leg_y + 48, label=False)
    surf.blit(FONT_SM.render("Cytochrome c + e\u207b", True, TEXT_COLOR), (leg_x + 14, leg_y + 40))

    surf.blit(FONT_SM.render("ATP", True, ATP_COLOR), (leg_x - 2, leg_y + 58))
    surf.blit(FONT_SM.render("= synthesized ATP", True, TEXT_COLOR), (leg_x + 28, leg_y + 58))


# ---------------------------------------------------------------------------
# Complex info data & click detection
# ---------------------------------------------------------------------------
COMPLEX_INFO = {
    "CI": {
        "name": "Complex I (NADH Dehydrogenase)",
        "category": "ETC Complex",
        "target": "CI",
        "description": "The largest complex in the ETC (45 subunits). Accepts 2 electrons from NADH and transfers them to ubiquinone (CoQ) via FMN and iron-sulfur clusters. Pumps 4 H+ from matrix to IMS per NADH oxidized.",
        "clinical_notes": "Mutations are the most common cause of mitochondrial disease. Can present as Leigh syndrome, MELAS, or Leber hereditary optic neuropathy (LHON)."
    },
    "CII": {
        "name": "Complex II (Succinate Dehydrogenase)",
        "category": "ETC Complex",
        "target": "CII",
        "description": "The only complex in both the TCA cycle and ETC. Oxidizes succinate to fumarate while reducing FAD to FADH2, then transfers electrons to CoQ. Does NOT pump protons \u2014 this is why FADH2 yields less ATP than NADH.",
        "clinical_notes": "Mutations cause paragangliomas and pheochromocytomas. Demonstrates the link between metabolic enzymes and cancer."
    },
    "CIII": {
        "name": "Complex III (Cytochrome bc1)",
        "category": "ETC Complex",
        "target": "CIII",
        "description": "Transfers electrons from ubiquinol (reduced CoQ) to cytochrome c via the Q-cycle. Translocates 4 H+ per pair of electrons. Contains cytochrome b, cytochrome c1, and the Rieske iron-sulfur protein.",
        "clinical_notes": "A major site of ROS production, especially when partially inhibited. ROS from Complex III is released into the IMS."
    },
    "CIV": {
        "name": "Complex IV (Cytochrome c Oxidase)",
        "category": "ETC Complex",
        "target": "CIV",
        "description": "The terminal oxidase. Receives electrons from cytochrome c and transfers them to O2 (the final electron acceptor), producing H2O. Pumps 2 H+ per electron pair. Contains copper centers (CuA, CuB) and heme groups.",
        "clinical_notes": "Target of cyanide, CO, and H2S poisoning. Its need for oxygen is why aerobic respiration requires O2."
    },
    "CV": {
        "name": "Complex V (ATP Synthase)",
        "category": "ATP Synthase",
        "target": "CV",
        "description": "A molecular rotary motor. Protons flow down their gradient through the Fo channel, driving rotation of the c-ring, which turns the gamma subunit inside F1, catalyzing ATP synthesis from ADP + Pi. ~4 H+ needed per ATP.",
        "clinical_notes": "One of the smallest known rotary engines in biology. Defects cause NARP syndrome (neuropathy, ataxia, retinitis pigmentosa)."
    }
}

def get_complex_at(mx, my):
    hit_rects = {
        "CI":   pygame.Rect(CX["CI"] - 80, MEMBRANE_Y - 75, 120, 160),
        "CII":  pygame.Rect(CX["CII"] - 35, MEMBRANE_Y + 25, 70, 60),
        "CIII": pygame.Rect(CX["CIII"] - 40, MEMBRANE_Y - 70, 80, 140),
        "CIV":  pygame.Rect(CX["CIV"] - 35, MEMBRANE_Y - 60, 70, 120),
        "CV":   pygame.Rect(CX["CV"] - 40, MEMBRANE_Y - 50, 80, 130),
    }
    for key, rect in hit_rects.items():
        if rect.collidepoint(mx, my):
            return key
    return None


def get_sidebar_chem_at(my, ui):
    list_y_start = ui["list_y_start"]
    item_h = ui["item_h"]
    visible_h = ui["visible_h"]
    if my < list_y_start or my > list_y_start + visible_h:
        return None
    for i, chem in enumerate(CHEMICALS):
        iy = list_y_start + i * item_h - sim.sidebar_scroll
        if iy <= my <= iy + item_h - 4:
            return chem
    return None


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    running = True
    dragging_slider = False
    ui = {}

    while running:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if sim.info_panel:
                        sim.info_panel = None
                    else:
                        running = False
                elif event.key == pygame.K_SPACE:
                    sim.paused = not sim.paused
                elif event.key == pygame.K_RIGHT and sim.paused:
                    sim_update()
                elif event.key == pygame.K_r:
                    saved = list(sim.active_chemicals)
                    sim.reset()
                    for c in saved:
                        sim.apply_chemical(c)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if sim.info_panel and sim.info_panel_rect:
                        if not sim.info_panel_rect.collidepoint(mx, my):
                            sim.info_panel = None
                            continue

                    if "pause" in ui and ui["pause"].collidepoint(mx, my):
                        sim.paused = not sim.paused
                    elif "step" in ui and ui["step"].collidepoint(mx, my):
                        sim.paused = True
                        sim_update()
                    elif "reset" in ui and ui["reset"].collidepoint(mx, my):
                        was_paused = sim.paused
                        sim.reset()
                        sim.paused = was_paused
                    elif "slider" in ui and ui["slider"].collidepoint(mx, my):
                        dragging_slider = True
                    elif mx < SIDEBAR_W and "list_y_start" in ui:
                        chem = get_sidebar_chem_at(my, ui)
                        if chem:
                            if chem["id"] in [c["id"] for c in sim.active_chemicals]:
                                sim.remove_chemical(chem["id"])
                            else:
                                sim.dragging_chem = chem
                                sim.drag_pos = (mx, my)
                    elif mx > SIDEBAR_W:
                        comp = get_complex_at(mx, my)
                        if comp:
                            sim.info_panel = COMPLEX_INFO.get(comp, {})

                elif event.button == 4:
                    if mx < SIDEBAR_W:
                        sim.sidebar_scroll = max(0, sim.sidebar_scroll - 30)
                elif event.button == 5:
                    if mx < SIDEBAR_W:
                        sim.sidebar_scroll = min(sim.sidebar_max_scroll, sim.sidebar_scroll + 30)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging_slider = False
                    if sim.dragging_chem:
                        if mx > SIDEBAR_W:
                            sim.apply_chemical(sim.dragging_chem)
                            sim.info_panel = sim.dragging_chem
                        sim.dragging_chem = None

            elif event.type == pygame.MOUSEMOTION:
                if dragging_slider and "slider" in ui:
                    sr = ui["slider"]
                    rel = (mx - sr.x) / sr.w
                    sim.flux = max(0.5, min(3.0, 0.5 + rel * 2.5))
                if sim.dragging_chem:
                    sim.drag_pos = (mx, my)

        # Right-click for info
        buttons = pygame.mouse.get_pressed()
        if buttons[2]:
            if mx < SIDEBAR_W and "list_y_start" in ui:
                chem = get_sidebar_chem_at(my, ui)
                if chem:
                    sim.info_panel = chem

        if not sim.paused:
            sim_update()

        ui = draw_all(mx, my)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
