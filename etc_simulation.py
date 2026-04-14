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
import webbrowser
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
FONT_TARGET = pygame.font.SysFont("Segoe UI", 22, bold=True)
FONT_ATP_RED = pygame.font.SysFont("Segoe UI", 22, bold=True)
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
# Load skull image for blocked complexes
# ---------------------------------------------------------------------------
skull_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "Gemini_Generated_Image_pcvvicpcvvicpcvv.png")
try:
    SKULL_IMG_RAW = pygame.image.load(skull_path).convert_alpha()
    SKULL_IMG = pygame.transform.smoothscale(SKULL_IMG_RAW, (40, 40))
    SKULL_IMG_LARGE = pygame.transform.smoothscale(SKULL_IMG_RAW, (120, 120))
except Exception:
    SKULL_IMG = None
    SKULL_IMG_LARGE = None

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

# Stationary CoQ and CytC station positions — visible labeled waypoints that
# electrons hop through, matching textbook ETC diagrams. Biologically these
# carriers are mobile pools, but the station-style simplification makes the
# electron flow pathway obvious for students. Stations sit INSIDE the upper
# portion of the membrane so electron hops travel within the lipid bilayer
# rather than arcing up into the IMS.
COQ_STATION_X = (CX["CII"] + CX["CIII"]) // 2 + 15
COQ_STATION_Y = IMS_BOTTOM + 10
CYTC_STATION_X = (CX["CIII"] + CX["CIV"]) // 2
CYTC_STATION_Y = IMS_BOTTOM + 10

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
    # Reaction equation shown on the OxygenAcceptor below CIV, not here.
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


def _draw_skull(surf, cx, cy, size=18, color=(255, 60, 60)):
    """Draw a skull and crossbones programmatically, no background."""
    s = size
    # Skull (circle + jaw)
    pygame.draw.circle(surf, color, (cx, cy - s // 3), s, 2)
    pygame.draw.ellipse(surf, color, (cx - s * 2 // 3, cy - s // 6, s * 4 // 3, s * 2 // 3), 2)
    # Eyes
    pygame.draw.circle(surf, color, (cx - s // 3, cy - s // 3), s // 5)
    pygame.draw.circle(surf, color, (cx + s // 3, cy - s // 3), s // 5)
    # Nose
    pygame.draw.polygon(surf, color, [(cx, cy - s // 8), (cx - s // 8, cy + s // 8), (cx + s // 8, cy + s // 8)])
    # Crossbones
    bx, by = cx, cy + s * 2 // 3
    bl = s
    pygame.draw.line(surf, color, (bx - bl, by - s // 3), (bx + bl, by + s // 3), 3)
    pygame.draw.line(surf, color, (bx + bl, by - s // 3), (bx - bl, by + s // 3), 3)
    # Bone ends (small circles)
    for dx, dy in [(-bl, -s // 3), (bl, s // 3), (bl, -s // 3), (-bl, s // 3)]:
        pygame.draw.circle(surf, color, (bx + dx, by + dy), 3)


def _draw_block_x(surf, cx, cy):
    txt = FONT_TINY.render("BLOCKED", True, (239, 83, 80))
    surf.blit(txt, (cx - txt.get_width() // 2, cy + 40))


def _draw_electron_payload(surf, x, y):
    """Draw the bright glowing electron payload carried by CoQ or Cyt c.
       Identical on both carriers so students track 'the electron' as the
       continuous element through the chain, even though the carriers differ."""
    # Outer soft glow
    glow = pygame.Surface((22, 22), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 234, 0, 60), (11, 11), 10)
    pygame.draw.circle(glow, (255, 234, 0, 110), (11, 11), 7)
    surf.blit(glow, (int(x) - 11, int(y) - 11))
    # Solid bright electron core
    pygame.draw.circle(surf, ELECTRON_COLOR, (int(x), int(y)), 5)
    pygame.draw.circle(surf, (255, 255, 220), (int(x), int(y)), 5, 1)


def draw_coq(surf, x, y, label=True):
    pts = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        pts.append((x + int(10 * math.cos(angle)), y + int(10 * math.sin(angle))))
    pygame.draw.polygon(surf, COQ_ORANGE, pts)
    pygame.draw.polygon(surf, (255, 160, 50), pts, 1)
    # Prominent electron payload - identical treatment on both carriers
    _draw_electron_payload(surf, x, y)
    if label:
        txt = FONT_TINY.render("CoQ", True, COQ_ORANGE)
        surf.blit(txt, (x - txt.get_width() // 2, y - 18))


def draw_cytc(surf, x, y, label=True):
    pygame.draw.circle(surf, CYTC_BLUE_LIGHT, (int(x), int(y)), 9)
    pygame.draw.circle(surf, (100, 130, 200), (int(x), int(y)), 9, 1)
    # Prominent electron payload - identical treatment on both carriers
    _draw_electron_payload(surf, x, y)
    if label:
        txt = FONT_TINY.render("Cyt c", True, CYTC_BLUE_LIGHT)
        surf.blit(txt, (int(x) - txt.get_width() // 2, int(y) - 20))


def draw_coq_station(surf, pulse=0):
    """Stationary CoQ pool marker sitting on the membrane between CII and CIII."""
    cx, cy = COQ_STATION_X, COQ_STATION_Y
    w, h = 50, 24
    if pulse > 0:
        glow = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        alpha = int(min(180, pulse * 14))
        pygame.draw.rect(glow, (255, 180, 50, alpha),
                         (12, 12, w, h), border_radius=12)
        surf.blit(glow, (cx - (w + 24) // 2, cy - (h + 24) // 2))
    rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surf, (55, 35, 18), rect, border_radius=12)
    pygame.draw.rect(surf, COQ_ORANGE, rect, 2, border_radius=12)
    txt = FONT_SM.render("CoQ", True, (255, 200, 120))
    surf.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))


def draw_cytc_station(surf, pulse=0):
    """Stationary cytochrome c pool marker between CIII and CIV."""
    cx, cy = CYTC_STATION_X, CYTC_STATION_Y
    w, h = 54, 24
    if pulse > 0:
        glow = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        alpha = int(min(180, pulse * 14))
        pygame.draw.rect(glow, (100, 160, 230, alpha),
                         (12, 12, w, h), border_radius=12)
        surf.blit(glow, (cx - (w + 24) // 2, cy - (h + 24) // 2))
    rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surf, (22, 30, 55), rect, border_radius=12)
    pygame.draw.rect(surf, CYTC_BLUE_LIGHT, rect, 2, border_radius=12)
    txt = FONT_SM.render("Cyt c", True, (160, 190, 235))
    surf.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))


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
    surf.blit(txt_ims, (SIM_X + 20, 42))
    txt_mat = FONT_MD.render("Mitochondrial Matrix", True, LABEL_DIM)
    surf.blit(txt_mat, (SIM_X + 20, HEIGHT - 40))


# ---------------------------------------------------------------------------
# Particle classes
# ---------------------------------------------------------------------------
class IMSProton:
    """A proton in the IMS. Spawns above the pumping complex that produced
       it, drifts with Brownian motion, and has a weak bias toward CV so a
       visible cluster of H+ accumulates above ATP synthase — matching the
       textbook presentation where H+ cluster above CV ready to flow back.
       Biologically a simplification: real IMS protons diffuse randomly and
       the gradient is a bulk concentration, not a directional flow."""

    def __init__(self, x, y):
        # Use the actual pumping position (slight jitter for visible spread)
        self.x = x + random.uniform(-6, 6)
        self.y = y + random.uniform(-6, 6)
        self.vx = random.uniform(-0.6, 0.6)
        self.vy = random.uniform(-0.6, 0.6)
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # Bounce within IMS bounds
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

        # Brownian random jitter — must dominate the drift so protons
        # actually disperse in 2D rather than forming vertical columns
        # that slowly drift rightward.
        self.vx += random.uniform(-0.22, 0.22)
        self.vy += random.uniform(-0.22, 0.22)

        # Very weak bias toward CV — a gentle long-term tendency, not
        # a conveyor belt. Kept far below the Brownian jitter.
        dx_to_cv = CX["CV"] - self.x
        if abs(dx_to_cv) > 4:
            self.vx += 0.006 * (1 if dx_to_cv > 0 else -1)

        # Looser damping + higher clamp so the random walk can actually
        # spread protons around the IMS instead of pinning them in place.
        self.vx *= 0.90
        self.vy *= 0.90
        self.vx = max(-1.2, min(1.2, self.vx))
        self.vy = max(-1.2, min(1.2, self.vy))

    def draw(self, surf):
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 4)


class PumpingProton:
    """A proton being actively pumped UP through a complex into IMS.
       Starts at an actual matrix proton's position (so students see matrix
       H+ entering the complex), travels up through the complex body while
       gently curving toward the complex's center x, and exits into the
       IMS at the target y."""
    def __init__(self, start_x, start_y, target_x, target_y):
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = 0.7 + random.random() * 0.4
        self.done = False

    def update(self, speed):
        self.y -= self.speed * speed
        dx = self.target_x - self.x
        self.x += dx * 0.08 * speed
        # Small random wobble so rising protons don't form a perfect column
        self.x += random.uniform(-0.4, 0.4)
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
       Starts at the position of the consumed IMS proton (so the cluster above
       CV is visibly drawn into the complex) and travels to the matrix side."""
    def __init__(self, cx, start_x=None, start_y=None):
        if start_x is None:
            start_x = cx + random.uniform(-4, 4)
        if start_y is None:
            start_y = MEMBRANE_Y - 40
        # Smoothly curve toward CV's vertical axis as the proton descends
        self.x = start_x
        self.y = start_y
        self.target_x = cx
        self.target_y = MATRIX_TOP + 60
        self.speed = 0.8 + random.random() * 0.4
        self.done = False

    def update(self, speed):
        # Descend mostly vertically with a gentle curve toward CV's center
        self.y += self.speed * speed
        dx = self.target_x - self.x
        self.x += dx * 0.06 * speed
        if self.y >= self.target_y:
            self.done = True

    def draw(self, surf):
        pygame.draw.circle(surf, PROTON_COLOR, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(surf, (150, 240, 255), (int(self.x), int(self.y)), 5, 1)
        ax, ay = int(self.x), int(self.y)
        pygame.draw.line(surf, PROTON_COLOR, (ax, ay + 6), (ax, ay + 14), 2)
        pygame.draw.line(surf, PROTON_COLOR, (ax - 4, ay + 10), (ax, ay + 14), 2)
        pygame.draw.line(surf, PROTON_COLOR, (ax + 4, ay + 10), (ax, ay + 14), 2)
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


class OxygenAcceptor:
    """Animated O2 final electron acceptor at CIV's matrix face.

       State machine:
         IDLE     - O2 bonded, gently vibrating, reaction equation visible
         SPLIT    - Electron arrives, O-O bond breaks, two O atoms slide apart
         ATTACH   - Four H atoms fly up from matrix and attach to the O atoms
         PRODUCTS - Two H2O molecules are visible; water particles spawn
         RESET    - Products fade, O2 reassembles, back to IDLE

       If a new electron arrives while a reaction is in progress, it is
       queued (capped at 3) and processed when the current reaction ends."""

    STATE_IDLE = 0
    STATE_SPLIT = 1
    STATE_ATTACH = 2
    STATE_PRODUCTS = 3
    STATE_RESET = 4

    SPLIT_DURATION = 16
    ATTACH_DURATION = 18
    PRODUCTS_DURATION = 28
    RESET_DURATION = 12

    BONDED_OFFSET = 8     # x offset from center when O atoms are bonded
    SPLIT_OFFSET = 22     # x offset from center when fully split

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = self.STATE_IDLE
        self.phase_age = 0
        self.vib = 0.0
        self.queue = 0
        self.left_ox_x = -self.BONDED_OFFSET
        self.right_ox_x = self.BONDED_OFFSET

    def trigger(self):
        if self.state == self.STATE_IDLE:
            self._start_reaction()
        else:
            self.queue = min(self.queue + 1, 3)

    def _start_reaction(self):
        self.state = self.STATE_SPLIT
        self.phase_age = 0

    def update(self):
        self.vib += 0.18
        if self.state == self.STATE_IDLE:
            return
        self.phase_age += 1

        if self.state == self.STATE_SPLIT:
            t = min(1.0, self.phase_age / self.SPLIT_DURATION)
            self.left_ox_x = -self.BONDED_OFFSET - t * (self.SPLIT_OFFSET - self.BONDED_OFFSET)
            self.right_ox_x = self.BONDED_OFFSET + t * (self.SPLIT_OFFSET - self.BONDED_OFFSET)
            if self.phase_age >= self.SPLIT_DURATION:
                self.state = self.STATE_ATTACH
                self.phase_age = 0

        elif self.state == self.STATE_ATTACH:
            if self.phase_age >= self.ATTACH_DURATION:
                self.state = self.STATE_PRODUCTS
                self.phase_age = 0

        elif self.state == self.STATE_PRODUCTS:
            if self.phase_age >= self.PRODUCTS_DURATION:
                self.state = self.STATE_RESET
                self.phase_age = 0
                # At the end, spawn a small water particle at the drifted
                # position so accumulated water continues drifting further
                # down through the matrix (continuity with legacy visual).
                drift = self.PRODUCTS_DURATION  # full drift distance
                sim.water_particles.append(
                    WaterParticle(self.x - self.SPLIT_OFFSET - 28,
                                  self.y + 12))
                sim.water_particles.append(
                    WaterParticle(self.x + self.SPLIT_OFFSET + 28,
                                  self.y + 12))

        elif self.state == self.STATE_RESET:
            # Positions are held at SPLIT_OFFSET while the draw() method
            # cross-fades the old split atoms out and new bonded atoms in.
            if self.phase_age >= self.RESET_DURATION:
                self.state = self.STATE_IDLE
                self.phase_age = 0
                self.left_ox_x = -self.BONDED_OFFSET
                self.right_ox_x = self.BONDED_OFFSET
                if self.queue > 0:
                    self.queue -= 1
                    self._start_reaction()

    def _draw_O(self, surf, cx, cy, color=(220, 60, 60),
                outline=(255, 170, 170), alpha=255):
        """Draw a single O atom with outline and 'O' label. Supports color
           (for orange-to-blue transition) and alpha (for cross-fade)."""
        if alpha <= 0:
            return
        a = max(0, min(255, int(alpha)))
        if a >= 255:
            pygame.draw.circle(surf, color, (cx, cy), 10)
            pygame.draw.circle(surf, outline, (cx, cy), 10, 2)
            lbl = FONT_TINY.render("O", True, (255, 255, 255))
            surf.blit(lbl, (cx - lbl.get_width() // 2, cy - 6))
            return
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, a), (12, 12), 10)
        pygame.draw.circle(s, (*outline, a), (12, 12), 10, 2)
        surf.blit(s, (cx - 12, cy - 12))
        lbl = FONT_TINY.render("O", True, (255, 255, 255))
        lbl.set_alpha(a)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy - 6))

    def _draw_H(self, surf, cx, cy, alpha=255):
        """Draw a single H atom with optional alpha."""
        if alpha <= 0:
            return
        a = max(0, min(255, int(alpha)))
        if a >= 255:
            pygame.draw.circle(surf, (230, 240, 255), (cx, cy), 5)
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 5, 1)
            lbl = FONT_TINY.render("H", True, (60, 100, 160))
            surf.blit(lbl, (cx - lbl.get_width() // 2, cy - 6))
            return
        s = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(s, (230, 240, 255, a), (7, 7), 5)
        pygame.draw.circle(s, (255, 255, 255, a), (7, 7), 5, 1)
        surf.blit(s, (cx - 7, cy - 7))
        lbl = FONT_TINY.render("H", True, (60, 100, 160))
        lbl.set_alpha(a)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy - 6))

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)

        # PRODUCTS: the orange O atoms visibly TRANSFORM into blue water
        # molecules (color shift) and drift outward + downward. H atoms
        # stay attached. This is the critical "the orange oxygens became
        # the blue water" pedagogical moment - they are the same atoms.
        if self.state == self.STATE_PRODUCTS:
            t = self.phase_age / self.PRODUCTS_DURATION
            # Drift outward and downward as water molecules move away
            drift_x = t * 28
            drift_y = t * 12
            # Color lerp from orange (220,60,60) to water blue (80,160,255).
            # Complete the color shift in the first 60% of the phase.
            color_t = min(1.0, t / 0.6)
            r = int(220 + (80 - 220) * color_t)
            g = int(60 + (160 - 60) * color_t)
            b = int(60 + (255 - 60) * color_t)
            color = (r, g, b)
            outline = (min(255, r + 60), min(255, g + 60), min(255, b + 30))
            # Fade out during the last 30% of the phase
            if t > 0.7:
                alpha = int(255 * max(0.0, 1 - (t - 0.7) / 0.3))
            else:
                alpha = 255
            for side in (-1, 1):
                wx = cx + side * (self.SPLIT_OFFSET + int(drift_x))
                wy = cy + int(drift_y)
                # H atoms attached at upper-left and upper-right (bent shape)
                self._draw_H(surf, wx - 9, wy - 8, alpha=alpha)
                self._draw_H(surf, wx + 9, wy - 8, alpha=alpha)
                # The (now-blue) O atom — same atom that was orange before
                self._draw_O(surf, wx, wy, color=color, outline=outline, alpha=alpha)
                # "H2O" label below
                lbl = FONT_SM.render("H\u2082O", True, (140, 200, 255))
                lbl.set_alpha(alpha)
                surf.blit(lbl, (wx - lbl.get_width() // 2, wy + 14))
            return

        # RESET: fresh O2 fades in at the center position (the previous
        # atoms already drifted away as water during PRODUCTS, so we
        # don't need to cross-fade them out anymore).
        if self.state == self.STATE_RESET:
            t = self.phase_age / self.RESET_DURATION
            fade_in_alpha = int(255 * min(1.0, t))
            bonded_lx = cx - self.BONDED_OFFSET
            bonded_rx = cx + self.BONDED_OFFSET
            self._draw_O(surf, bonded_lx, cy, alpha=fade_in_alpha)
            self._draw_O(surf, bonded_rx, cy, alpha=fade_in_alpha)
            bond = pygame.Surface((12, 8), pygame.SRCALPHA)
            pygame.draw.line(bond, (230, 230, 230, fade_in_alpha),
                             (0, 2), (11, 2), 2)
            pygame.draw.line(bond, (230, 230, 230, fade_in_alpha),
                             (0, 6), (11, 6), 2)
            surf.blit(bond, (bonded_lx + 5, cy - 4))
            return

        # IDLE / SPLIT / ATTACH — draw the orange O atoms at current positions
        if self.state == self.STATE_IDLE:
            vib_y = int(math.sin(self.vib) * 1.8)
            vib_x_l = int(math.cos(self.vib * 1.3) * 1.0)
            vib_x_r = int(math.cos(self.vib * 1.3 + 0.5) * 1.0)
        else:
            vib_y = vib_x_l = vib_x_r = 0

        lx = cx + int(self.left_ox_x) + vib_x_l
        rx = cx + int(self.right_ox_x) + vib_x_r
        oy = cy + vib_y

        # Bond between O atoms (visible when close)
        gap = rx - lx
        if gap < 28:
            bond_alpha = max(0, min(255, int((28 - gap) * 16)))
            bond = pygame.Surface((gap - 10, 8), pygame.SRCALPHA)
            pygame.draw.line(bond, (230, 230, 230, bond_alpha),
                             (0, 2), (gap - 10, 2), 2)
            pygame.draw.line(bond, (230, 230, 230, bond_alpha),
                             (0, 6), (gap - 10, 6), 2)
            surf.blit(bond, (lx + 5, oy - 4))

        # Two orange O atoms
        self._draw_O(surf, lx, oy)
        self._draw_O(surf, rx, oy)

        # SPLIT phase - electron sparkle between the separating atoms
        if self.state == self.STATE_SPLIT:
            t = self.phase_age / self.SPLIT_DURATION
            alpha = int(255 * min(1.0, t * 2))
            e_glow = pygame.Surface((22, 22), pygame.SRCALPHA)
            pygame.draw.circle(e_glow, (255, 234, 0, int(alpha * 0.4)), (11, 11), 10)
            pygame.draw.circle(e_glow, (255, 234, 0, alpha), (11, 11), 6)
            surf.blit(e_glow, (cx - 11, cy - 11))
            e_lbl = FONT_TINY.render("e\u207b", True, (255, 234, 0))
            e_lbl.set_alpha(alpha)
            surf.blit(e_lbl, (cx - e_lbl.get_width() // 2, cy + 14))

        # ATTACH phase - H atoms flying up from matrix toward each O
        if self.state == self.STATE_ATTACH:
            t = min(1.0, self.phase_age / self.ATTACH_DURATION)
            # Four H atoms: 2 per O atom
            for ox_center, h_offs in [(lx, [-8, 8]), (rx, [-8, 8])]:
                for hx_off in h_offs:
                    start_x = ox_center + hx_off
                    start_y = cy + 55
                    target_x = ox_center + hx_off * 0.7
                    target_y = cy + (hx_off // 2)
                    hx_now = start_x + (target_x - start_x) * t
                    hy_now = start_y + (target_y - start_y) * t
                    self._draw_H(surf, int(hx_now), int(hy_now))

        # PRODUCTS phase - "H2O" labels flanking the atoms, fading slowly
        if self.state == self.STATE_PRODUCTS:
            t = self.phase_age / self.PRODUCTS_DURATION
            alpha = int(255 * max(0.0, 1 - t * 0.7))
            for ox_center in [lx, rx]:
                # Small H atoms still attached
                self._draw_H(surf, ox_center - 7, cy - 8)
                self._draw_H(surf, ox_center + 7, cy - 8)
                lbl = FONT_SM.render("H\u2082O", True, (120, 190, 255))
                lbl.set_alpha(alpha)
                surf.blit(lbl, (ox_center - lbl.get_width() // 2, cy + 16))

        # Static labels visible only in IDLE state
        if self.state == self.STATE_IDLE:
            lbl = FONT_MD.render("O\u2082", True, (255, 180, 180))
            surf.blit(lbl, (cx - lbl.get_width() // 2, cy + 16))
            hint = FONT_TINY.render("final e\u207b acceptor", True, (200, 150, 150))
            surf.blit(hint, (cx - hint.get_width() // 2, cy + 36))
            eq = FONT_TINY.render("O\u2082 + 4e\u207b + 4H\u207a \u2192 2 H\u2082O",
                                  True, (180, 180, 200))
            surf.blit(eq, (cx - eq.get_width() // 2, cy + 50))


class SubstrateEntry:
    """NADH or FADH2 substrate marker rising from the matrix into CI or CII.
       Visualizes where electrons enter the chain.
       The `visible` flag lets us suppress rendering without removing the
       spawn logic — used to hide FADH2 at CII for the current game level
       while keeping the code intact for a future 'Level 2' reveal."""
    def __init__(self, cx, label, color, visible=True):
        self.x = cx + random.uniform(-6, 6)
        self.y = MATRIX_TOP + 70
        self.target_y = MEMBRANE_Y + 18
        self.label = label
        self.color = color
        self.visible = visible
        self.alpha = 255
        self.age = 0

    def update(self):
        self.age += 1
        if self.age < 28:
            dy = self.target_y - self.y
            self.y += dy * 0.12
        else:
            self.alpha -= 10

    def draw(self, surf):
        if not self.visible:
            return
        if self.alpha <= 0:
            return
        a = int(max(0, min(255, self.alpha)))
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (8, 8), 6)
        pygame.draw.circle(s, (255, 255, 255, a), (8, 8), 6, 1)
        surf.blit(s, (int(self.x) - 8, int(self.y) - 8))
        lbl = FONT_TINY.render(self.label, True, self.color)
        lbl.set_alpha(a)
        surf.blit(lbl, (int(self.x) + 9, int(self.y) - 6))


class ElectronHandoff:
    """Brief electron sparkle tracking the CoQ -> CytC handoff through CIII.
       Travels upward through the complex so the electron visibly continues
       rather than appearing to vanish and reappear."""
    def __init__(self, cx, y_start, y_end, duration=16):
        self.x = cx
        self.y_start = y_start
        self.y_end = y_end
        self.duration = duration
        self.age = 0

    def update(self):
        self.age += 1

    @property
    def done(self):
        return self.age >= self.duration

    def draw(self, surf):
        if self.done:
            return
        t = self.age / self.duration
        y = self.y_start + (self.y_end - self.y_start) * t
        alpha = int(255 * (1 - abs(t - 0.5) * 1.4))
        alpha = max(60, min(255, alpha))
        for radius, a_mult in [(10, 0.22), (6, 0.5), (3, 1.0)]:
            s = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 230, 90, int(alpha * a_mult)),
                               (radius + 1, radius + 1), radius)
            surf.blit(s, (int(self.x) - radius - 1, int(y) - radius - 1))


class ElectronDescent:
    """Electron descending through CIV from the CytC docking site down to the
       matrix side, where it combines with O2 + 2 H+ to form H2O."""
    def __init__(self, cx, y_start, y_end, duration=28):
        self.x = cx
        self.y_start = y_start
        self.y_end = y_end
        self.duration = duration
        self.age = 0
        self.spawned_water = False

    def update(self):
        self.age += 1
        if self.age >= self.duration and not self.spawned_water:
            # Electron arrives at O2 acceptor - trigger reaction pulse and
            # spawn the resulting water droplet from the O2 position.
            sim.oxygen_acceptor.trigger()
            sim.water_particles.append(WaterParticle(self.x, self.y_end + 12))
            self.spawned_water = True

    @property
    def done(self):
        return self.age >= self.duration + 8

    def draw(self, surf):
        if self.age >= self.duration:
            return
        t = self.age / self.duration
        # Ease-in so it accelerates downward
        y = self.y_start + (self.y_end - self.y_start) * (t * t)
        for radius, a_mult in [(10, 0.22), (6, 0.5), (3, 1.0)]:
            s = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 230, 90, int(220 * a_mult)),
                               (radius + 1, radius + 1), radius)
            surf.blit(s, (int(self.x) - radius - 1, int(y) - radius - 1))
        # Label near the moving electron
        if self.age < self.duration - 4:
            lbl = FONT_TINY.render("e\u207b", True, (255, 230, 90))
            surf.blit(lbl, (int(self.x) + 8, int(y) - 6))


class ElectronHop:
    """A glowing electron traveling along a curved path from a source point to
       a destination. Used to show electron transfer steps between a complex
       and a CoQ/CytC station, or between a station and the next complex.
       Each hop carries a 'phase' string so the sim_update loop can dispatch
       what happens next when the hop arrives (activate next complex, park at
       station when blocked, etc.).

       After arriving at the destination, the hop is kept on screen for a
       'linger' period — clamped at the endpoint — so students can clearly
       see the electron REACH the station or complex before the next hop
       takes over. Without the linger, the last drawn frame is 1-2 pixels
       short of the destination, which reads visually as 'fading out'."""
    def __init__(self, phase, sx, sy, ex, ey, duration=22, control_offset=35):
        self.phase = phase
        self.sx, self.sy = sx, sy
        self.ex, self.ey = ex, ey
        self.duration = duration
        self.linger = 18  # frames to hold at endpoint before disappearing
        self.age = 0.0
        self.dispatched = False
        # Quadratic Bezier control point creates a subtle upward arc
        self.mcx = (sx + ex) / 2
        self.mcy = (sy + ey) / 2 - control_offset

    def update(self, speed=1.0):
        self.age += speed

    @property
    def arrived(self):
        return self.age >= self.duration

    @property
    def done(self):
        return self.age >= self.duration + self.linger

    def _pos(self):
        t = min(1.0, self.age / self.duration)
        inv = 1 - t
        x = inv * inv * self.sx + 2 * inv * t * self.mcx + t * t * self.ex
        y = inv * inv * self.sy + 2 * inv * t * self.mcy + t * t * self.ey
        return x, y

    def draw(self, surf):
        if self.done:
            return
        # During travel: use bezier position. During linger: clamp at endpoint
        # so the electron visibly PARKS at the station before fading.
        if self.age >= self.duration:
            x, y = self.ex, self.ey
            # Fade out over the linger period
            linger_t = (self.age - self.duration) / self.linger
            fade = max(0.0, 1.0 - linger_t)
        else:
            x, y = self._pos()
            fade = 1.0
        # Identical electron glow treatment as the carrier payload so the
        # student tracks the same visual element through every transfer step.
        glow_alpha_outer = int(60 * fade)
        glow_alpha_inner = int(110 * fade)
        core_alpha = int(255 * fade)
        glow = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 234, 0, glow_alpha_outer), (11, 11), 10)
        pygame.draw.circle(glow, (255, 234, 0, glow_alpha_inner), (11, 11), 7)
        surf.blit(glow, (int(x) - 11, int(y) - 11))
        core = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(core, (255, 234, 0, core_alpha), (6, 6), 5)
        pygame.draw.circle(core, (255, 255, 220, core_alpha), (6, 6), 5, 1)
        surf.blit(core, (int(x) - 6, int(y) - 6))


class CoQShuttle:
    """Ubiquinone carrying electrons LATERALLY within the membrane from CI/CII to CIII.
       spawn_delay holds the shuttle invisible at start_x for N frames before it
       becomes visible and begins moving. Used so that CII's electron rise can
       visibly complete before the CoQ picks up the electron."""
    def __init__(self, start_x, end_x, spawn_delay=0):
        self.x = start_x
        self.y = MEMBRANE_Y + random.uniform(-8, 8)
        self.end_x = end_x
        self.speed = 1.8
        self.alive = True
        self.arrived = False
        self.stuck = False  # True when CIII is backed up
        self.wobble = random.uniform(0, 2 * math.pi)
        self.spawn_delay = spawn_delay

    def update(self, speed):
        if self.spawn_delay > 0:
            self.spawn_delay -= 1
            return
        if self.stuck:
            self.wobble += 0.05
            self.x = self.end_x - 20 + math.sin(self.wobble) * 10
            return
        dx = self.end_x - self.x
        if abs(dx) < 5:
            self.alive = False
            self.arrived = True
        else:
            self.x += (dx / abs(dx)) * self.speed * speed

    def draw(self, surf):
        if self.spawn_delay > 0:
            return
        draw_coq(surf, int(self.x), int(self.y), label=False)
        if self.stuck:
            pygame.draw.circle(surf, (255, 80, 80), (int(self.x), int(self.y)), 12, 1)


class CytCShuttle:
    """Cytochrome c carrying electrons along IMS (above membrane) from CIII to CIV."""
    def __init__(self, start_x, end_x):
        self.x = start_x
        self.y = IMS_BOTTOM - 15 + random.uniform(-3, 3)
        self.end_x = end_x
        self.speed = 2.0
        self.alive = True
        self.arrived = False
        self.stuck = False  # True when CIV is blocked - piles up at CIV
        self.wobble = random.uniform(0, 2 * math.pi)

    def update(self, speed):
        if self.stuck:
            # Jitter in place near CIV to show it's stuck
            self.wobble += 0.05
            self.x = self.end_x + math.sin(self.wobble) * 8
            self.y = IMS_BOTTOM - 15 + math.cos(self.wobble * 0.7) * 5
            return
        dx = self.end_x - self.x
        if abs(dx) < 5:
            self.alive = False
            self.arrived = True
        else:
            self.x += (dx / abs(dx)) * self.speed * speed

    def draw(self, surf):
        draw_cytc(surf, self.x, self.y, label=False)
        if self.stuck:
            # Red outline to show it's stuck
            pygame.draw.circle(surf, (255, 80, 80), (int(self.x), int(self.y)), 11, 1)


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
        # Pre-populate the IMS with a living-cell H+ distribution so the
        # gradient is visible from frame 0. Uniform spread plus extra
        # density above each pumping complex and ATP synthase.
        for _ in range(35):
            self.ims_protons.append(IMSProton(
                random.randint(SIM_X + 30, WIDTH - 30),
                random.randint(25, IMS_BOTTOM - 20)))
        for cx in (CX["CI"], CX["CIII"], CX["CIV"], CX["CV"]):
            for _ in range(12):
                self.ims_protons.append(IMSProton(
                    cx + random.randint(-45, 45),
                    random.randint(25, IMS_BOTTOM - 30)))
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
        self.substrate_entries = []   # NADH/FADH2 entry markers at CI/CII
        self.electron_handoffs = []   # legacy visual sparkles (reused for CII rise)
        self.electron_descents = []   # electron descending through CIV to water
        self.electron_hops = []       # electron hops between complexes and stations
        self.parked_at_coq = []       # electrons held at CoQ station when CIII blocked
        self.parked_at_cytc = []      # electrons held at CytC station when CIV blocked
        self.coq_station_pulse = 0    # brief highlight when CoQ receives/sends
        self.cytc_station_pulse = 0   # same for CytC station
        # Persistent O2 final electron acceptor at CIV's matrix face
        self.oxygen_acceptor = OxygenAcceptor(CX["CIV"], MATRIX_TOP + 35)

        # Complex activation flash timers (frames remaining)
        self.complex_active = {"CI": 0, "CII": 0, "CIII": 0, "CIV": 0, "CV": 0}

        self.atp_count = 0
        self.atp_rate = 0.0
        self.atp_history = []

        self.cv_rotation = 0.0
        self.frame = 0
        self.flux = 0.75
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
        self.ref_link_rect = None
        self.ref_link_url = None
        self.sidebar_scroll = 0
        self.sidebar_max_scroll = 0
        self.dragging_chem = None
        self.drag_pos = (0, 0)
        self.hovered_complex = None

        # Electron backup tracking
        self.stuck_cytc_count = 0
        self.stuck_coq_count = 0
        self.ciii_backed_up = False
        self.ci_backed_up = False
        self.chain_status = "normal"

        # Narrative cascade system
        self.narrative_events = []
        self.narrative_queue = []
        self.narrative_timer = 0

        # Toxin alert overlay (large blinking skull with name)
        self.toxin_alert_name = None
        self.toxin_alert_full = None
        self.toxin_alert_target = None   # complex key like "CIV", "CI", "membrane"
        self.toxin_alert_timer = 0

        # Gradient counter for HUD
        self.gradient_display = 0

    def apply_chemical(self, chem):
        if chem["id"] in [c["id"] for c in self.active_chemicals]:
            return
        self.active_chemicals.append(chem)
        self._apply_effect(chem)
        self._trigger_narrative(chem)

    def remove_chemical(self, chem_id):
        self.active_chemicals = [c for c in self.active_chemicals if c["id"] != chem_id]
        self.blocked = {"CI": False, "CII": False, "CIII": False, "CIV": False, "CV": False}
        self.partial_block = {"CI": False}
        self.uncoupled = False
        self.uncoupler_strength = 0.0
        self.transport_blocked = False
        self.ros_generating = {"CI": False}
        # Clear narrative and toxin alert
        self.narrative_events = []
        self.narrative_queue = []
        self.narrative_timer = 0
        self.toxin_alert_name = None
        self.toxin_alert_full = None
        self.toxin_alert_target = None
        self.toxin_alert_timer = 0
        # Clear parked electrons and any in-flight hops so the chain resumes clean
        self.parked_at_coq = []
        self.parked_at_cytc = []
        self.electron_hops = []
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

    # Short display names for toxin alert overlay
    TOXIN_SHORT_NAMES = {
        "carbon_monoxide": "CO",
        "cyanide": "CN\u207b",
        "hydrogen_sulfide": "H\u2082S",
        "azide": "NaN\u2083",
        "rotenone": "ROT",
        "piericidin_a": "PierA",
        "barbiturates": "BARB",
        "antimycin_a": "AA",
        "myxothiazol": "MYX",
        "oligomycin": "OLI",
        "dnp": "DNP",
        "fccp": "FCCP",
        "cccp": "CCCP",
        "malonate": "MAL",
        "ttfa": "TTFA",
        "atractyloside": "ATR",
        "metformin": "MET",
        "mptp": "MPP\u207a",
        "doxorubicin": "DOX",
        "thermogenin": "UCP1",
    }

    def _trigger_narrative(self, chem):
        """Queue a timed narrative cascade for the applied chemical."""
        self.narrative_events = []
        self.narrative_queue = []
        self.narrative_timer = 0

        # Set toxin alert overlay
        self.toxin_alert_name = self.TOXIN_SHORT_NAMES.get(chem["id"], chem["name"][:6])
        self.toxin_alert_full = chem["name"]
        self.toxin_alert_target = chem["target"]
        self.toxin_alert_timer = 0

        target = chem["target"]
        effect = chem["effect"]
        name = chem["name"]

        if effect == "block" and target == "CIV":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} binds Complex IV (cytochrome c oxidase)",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "Electron transfer to O\u2082 is BLOCKED \u2014 no water produced",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "Cytochrome c backs up at Complex IV \u2014 cannot deliver electrons",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "Complex III backs up \u2014 CoQ cannot offload electrons",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 125},
                {"delay": 500, "text": "Complex I stops pumping \u2014 entire ETC is frozen",
                 "color": (255, 100, 100), "duration": 300, "y_pos": 150},
                {"delay": 650, "text": "H\u207a gradient collapsing \u2014 no new protons pumped into IMS",
                 "color": (255, 80, 80), "duration": 400, "y_pos": 175},
                {"delay": 850, "text": "ATP production STOPS \u2014 cell energy crisis!",
                 "color": (255, 50, 50), "duration": 500, "y_pos": 200},
            ]

        elif effect == "block" and target == "CIII":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} binds Complex III (cytochrome bc\u2081)",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "Electron transfer from CoQ to Cyt c is BLOCKED",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "CoQ backs up \u2014 Complex I and Complex II cannot offload electrons",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "H\u207a pumping stops at Complex I and Complex III \u2014 gradient collapsing",
                 "color": (255, 100, 100), "duration": 300, "y_pos": 125},
                {"delay": 500, "text": "Partial electron transfer generates ROS (superoxide O\u2082\u207b)",
                 "color": (255, 50, 50), "duration": 400, "y_pos": 150},
                {"delay": 700, "text": "ATP production STOPS \u2014 oxidative damage!",
                 "color": (255, 50, 50), "duration": 500, "y_pos": 175},
            ]

        elif effect == "block" and target == "CI":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} blocks Complex I (NADH dehydrogenase)",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "NADH cannot donate electrons \u2014 CI is inhibited",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "FADH\u2082 via Complex II still works \u2014 partial electron flow remains",
                 "color": (200, 200, 100), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "H\u207a pumping reduced ~60% \u2014 gradient weakens",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 125},
                {"delay": 500, "text": "ATP production drops significantly",
                 "color": (255, 100, 100), "duration": 400, "y_pos": 150},
            ]

        elif effect == "block" and target == "CII":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} blocks Complex II (succinate dehydrogenase)",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "FADH\u2082 cannot donate electrons \u2014 Complex II inhibited",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "NADH via CI still works \u2014 most electron flow continues",
                 "color": (200, 200, 100), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "ATP production reduced ~20%",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 125},
            ]

        elif effect == "block" and target == "CV":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} blocks the F\u2080 proton channel of ATP synthase",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "Protons CANNOT flow back into matrix through CV",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "H\u207a gradient builds to maximum \u2014 backpressure on ETC",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "ETC slows \u2014 too much gradient resistance to pump more H\u207a",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 125},
                {"delay": 500, "text": "ATP synthesis STOPS \u2014 despite intact electron transport!",
                 "color": (255, 50, 50), "duration": 500, "y_pos": 150},
            ]

        elif effect == "uncouple":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} \u2014 protonophore inserted into membrane",
                 "color": (255, 152, 0), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "H\u207a leaks across membrane \u2014 bypasses ATP synthase",
                 "color": (255, 180, 50), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "ETC runs FASTER (no backpressure) \u2014 O\u2082 consumption increases",
                 "color": (200, 200, 100), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "Proton gradient dissipated as HEAT instead of ATP",
                 "color": (255, 150, 50), "duration": 300, "y_pos": 125},
                {"delay": 500, "text": "ATP production drops \u2014 energy wasted as heat!",
                 "color": (255, 80, 80), "duration": 400, "y_pos": 150},
            ]

        elif effect == "partial_block" and target == "CI":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} mildly inhibits Complex I",
                 "color": (200, 200, 100), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "NADH electron flow reduced \u2014 not fully blocked",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "Lower ATP \u2192 AMPK activated \u2192 increases glucose uptake",
                 "color": (100, 200, 100), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "Therapeutic effect: helps control blood sugar in diabetes",
                 "color": (100, 200, 255), "duration": 400, "y_pos": 125},
            ]

        elif effect == "ros_generation":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} accepts electrons from Complex I",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "Electrons transferred directly to O\u2082 \u2192 superoxide (O\u2082\u207b)",
                 "color": (255, 100, 100), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "Reactive oxygen species (ROS) damage mitochondrial components",
                 "color": (255, 50, 50), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "Cardiotoxicity \u2014 high mitochondrial density in heart cells",
                 "color": (255, 50, 50), "duration": 400, "y_pos": 125},
            ]

        elif effect == "transport_block":
            self.narrative_queue = [
                {"delay": 0,   "text": f"{name} blocks adenine nucleotide translocase (ANT)",
                 "color": (255, 80, 80), "duration": 300, "y_pos": 50},
                {"delay": 90,  "text": "ATP cannot exit mitochondria \u2014 ADP cannot enter",
                 "color": (255, 150, 80), "duration": 300, "y_pos": 75},
                {"delay": 200, "text": "ATP accumulates inside \u2014 feedback inhibits ATP synthase",
                 "color": (255, 200, 80), "duration": 300, "y_pos": 100},
                {"delay": 350, "text": "Cell starved of ATP despite mitochondria producing it!",
                 "color": (255, 50, 50), "duration": 400, "y_pos": 125},
            ]

    def update_narrative(self):
        """Advance the narrative timer and fire queued events."""
        self.narrative_timer += 1

        # Fire queued events whose delay has passed
        remaining = []
        for evt in self.narrative_queue:
            if self.narrative_timer >= evt["delay"]:
                self.narrative_events.append({
                    "text": evt["text"],
                    "color": evt["color"],
                    "y_pos": evt["y_pos"],
                    "age": 0,
                })
            else:
                remaining.append(evt)
        self.narrative_queue = remaining

        # Age events (for fade-in effect only)
        for evt in self.narrative_events:
            evt["age"] += 1
        # Events persist - they are only cleared when chemicals are removed

        # Tick toxin alert
        if self.toxin_alert_name:
            self.toxin_alert_timer += 1


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

    # --- Cascade backup logic (station-based) ---
    # Count parked electrons at each station to determine backup state.
    sim.stuck_coq_count = len(sim.parked_at_coq)
    sim.stuck_cytc_count = len(sim.parked_at_cytc)

    # CoQ station full -> CI/CII cannot offload to CoQ (= "ci_backed_up")
    sim.ci_backed_up = sim.stuck_coq_count >= 5
    # CytC station full -> CIII cannot offload to CytC (= "ciii_backed_up")
    sim.ciii_backed_up = sim.stuck_cytc_count >= 5

    if sim.ci_backed_up:
        sim.chain_status = "blocked"
    elif sim.ciii_backed_up or sim.stuck_cytc_count > 0 or sim.stuck_coq_count > 0:
        sim.chain_status = "backing_up"
    else:
        sim.chain_status = "normal"

    # --- Step 1: NADH donates electrons to Complex I, which hops e- to CoQ ---
    # Hop path stays WITHIN the membrane bilayer (CoQ is a lipid-soluble
    # carrier that resides inside the membrane).
    spawn_nadh = max(1, int(55 / flux))
    ci_can_work = ci_rate > 0 and not sim.blocked["CI"] and not sim.ci_backed_up
    if ci_can_work and f % spawn_nadh == 0:
        if ci_rate < 1.0 and random.random() > ci_rate:
            pass
        else:
            sim.complex_active["CI"] = 20
            _pump_protons("CI", 4)
            sim.substrate_entries.append(
                SubstrateEntry(CX["CI"], "NADH", (120, 220, 255)))
            sim.electron_hops.append(ElectronHop(
                "to_CoQ",
                CX["CI"] + 35, MEMBRANE_Y,
                COQ_STATION_X, COQ_STATION_Y,
                duration=22, control_offset=3))

    # --- Step 2: FADH2 donates electrons to Complex II, which hops e- to CoQ ---
    spawn_fadh2 = max(1, int(80 / flux))
    cii_can_work = cii_rate > 0 and not sim.blocked["CII"] and not sim.ci_backed_up
    if cii_can_work and f % spawn_fadh2 == 0:
        sim.complex_active["CII"] = 20
        # FADH2 entry marker is spawned but hidden for current game level;
        # re-enable by setting visible=True for a future "Level 2" reveal.
        sim.substrate_entries.append(
            SubstrateEntry(CX["CII"], "FADH\u2082", (255, 180, 100), visible=False))
        # Start at CII's TOP edge (y=408, where CII meets the membrane) so
        # the yellow electron is visible against the dark membrane rather
        # than blending with CII's red body. The electron then curves up
        # through the membrane to the CoQ station. Slow duration so the
        # less-frequent FADH2 contribution is clearly trackable.
        sim.electron_hops.append(ElectronHop(
            "to_CoQ",
            CX["CII"], MEMBRANE_Y + 28,
            COQ_STATION_X, COQ_STATION_Y,
            duration=32, control_offset=14))

    # --- Step 3: Process electron hops, dispatching phase transitions ---
    spawned_hops = []
    for h in sim.electron_hops:
        h.update(flux)
        if h.arrived and not h.dispatched:
            h.dispatched = True
            if h.phase == "to_CoQ":
                sim.coq_station_pulse = 35
                if ciii_ok and not sim.ciii_backed_up:
                    # Continue: CoQ station -> CIII (stays within membrane)
                    spawned_hops.append(ElectronHop(
                        "to_CIII",
                        COQ_STATION_X, COQ_STATION_Y,
                        CX["CIII"] - 35, MEMBRANE_Y,
                        duration=22, control_offset=3))
                else:
                    # CIII blocked or backed up - park electron at CoQ station
                    if len(sim.parked_at_coq) < 8:
                        sim.parked_at_coq.append({
                            "wobble": random.uniform(0, 2 * math.pi),
                            "phase_offset": random.uniform(-0.5, 0.5),
                        })
            elif h.phase == "to_CIII":
                # Electron arrives at CIII: activate, pump, then hop to CytC
                sim.complex_active["CIII"] = 20
                _pump_protons("CIII", 4)
                spawned_hops.append(ElectronHop(
                    "to_CytC",
                    CX["CIII"] + 35, MEMBRANE_Y,
                    CYTC_STATION_X, CYTC_STATION_Y,
                    duration=22, control_offset=3))
            elif h.phase == "to_CytC":
                sim.cytc_station_pulse = 35
                if civ_ok:
                    # Continue: CytC station -> CIV (stays within membrane)
                    spawned_hops.append(ElectronHop(
                        "to_CIV",
                        CYTC_STATION_X, CYTC_STATION_Y,
                        CX["CIV"] - 35, MEMBRANE_Y,
                        duration=22, control_offset=3))
                else:
                    # CIV blocked - park electron at CytC station
                    if len(sim.parked_at_cytc) < 8:
                        sim.parked_at_cytc.append({
                            "wobble": random.uniform(0, 2 * math.pi),
                            "phase_offset": random.uniform(-0.5, 0.5),
                        })
            elif h.phase == "to_CIV":
                # Electron arrives at CIV: activate, pump, begin descent to water
                sim.complex_active["CIV"] = 20
                _pump_protons("CIV", 2)
                _consume_matrix_protons_for_water("CIV", 2)
                sim.electron_descents.append(
                    ElectronDescent(CX["CIV"], MEMBRANE_Y, MATRIX_TOP + 35))
    sim.electron_hops.extend(spawned_hops)
    sim.electron_hops = [h for h in sim.electron_hops if not h.done]

    # --- Station pulses decay ---
    if sim.coq_station_pulse > 0:
        sim.coq_station_pulse -= 1
    if sim.cytc_station_pulse > 0:
        sim.cytc_station_pulse -= 1

    # --- Release parked electrons when downstream blocks clear ---
    release_interval = max(1, int(18 / flux))
    if ciii_ok and not sim.ciii_backed_up and sim.parked_at_coq and f % release_interval == 0:
        sim.parked_at_coq.pop(0)
        sim.electron_hops.append(ElectronHop(
            "to_CIII",
            COQ_STATION_X, COQ_STATION_Y,
            CX["CIII"] - 35, MEMBRANE_Y,
            duration=22, control_offset=3))
        sim.coq_station_pulse = 20
    if civ_ok and sim.parked_at_cytc and f % release_interval == 0:
        sim.parked_at_cytc.pop(0)
        sim.electron_hops.append(ElectronHop(
            "to_CIV",
            CYTC_STATION_X, CYTC_STATION_Y,
            CX["CIV"] - 35, MEMBRANE_Y,
            duration=22, control_offset=3))
        sim.cytc_station_pulse = 20

    # --- Update parked electron wobble phase ---
    for p in sim.parked_at_coq:
        p["wobble"] += 0.06
    for p in sim.parked_at_cytc:
        p["wobble"] += 0.06

    # --- Step 5: Pumping protons travel upward into IMS ---
    for p in sim.pumping_protons:
        p.update(flux)
    # Convert finished pumping protons into persistent IMS protons
    for p in sim.pumping_protons:
        if p.done:
            if len(sim.ims_protons) < IMS_PROTON_CAP:
                sim.ims_protons.append(IMSProton(p.x, p.target_y))

    # (No anti-clustering redistribution — protons are allowed to cluster
    # above the pumping complexes and drift toward CV for visible gradient.)
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
        # Pick the IMS proton closest to CV's top by 2D distance, so the
        # protons visibly hovering near ATP synthase are the ones drawn
        # into the enzyme. ATP synthesis is reliable whenever a gradient
        # exists.
        cv_top_x = CX["CV"]
        cv_top_y = IMS_BOTTOM - 30
        best_idx = 0
        best_dist = 99999
        for i, p in enumerate(sim.ims_protons):
            d = (p.x - cv_top_x) ** 2 + (p.y - cv_top_y) ** 2
            if d < best_dist:
                best_dist = d
                best_idx = i
        sim.ims_protons.pop(best_idx)
        # Spawn the descending InfluxProton from a random position within
        # the visible decorative cluster above CV, so students see one of
        # the visible H+ "dropping" into the channel.
        start_x = CX["CV"] + random.uniform(-22, 22)
        start_y = IMS_BOTTOM - 42 + random.uniform(-14, 6)
        sim.influx_protons.append(
            InfluxProton(CX["CV"], start_x=start_x, start_y=start_y))
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
            # ~3 H+ per ATP (within the biologically reasonable range)
            if random.random() < 1 / 3:
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

    # --- Substrate entry markers (NADH at CI, FADH2 at CII) ---
    for se in sim.substrate_entries:
        se.update()
    sim.substrate_entries = [se for se in sim.substrate_entries if se.alpha > 0]

    # --- Electron handoff sparkles at CIII (CoQ -> CytC) ---
    for eh in sim.electron_handoffs:
        eh.update()
    sim.electron_handoffs = [eh for eh in sim.electron_handoffs if not eh.done]

    # --- Electron descents through CIV (to water) ---
    for ed in sim.electron_descents:
        ed.update()
    sim.electron_descents = [ed for ed in sim.electron_descents if not ed.done]

    # --- Oxygen acceptor pulse decay ---
    sim.oxygen_acceptor.update()

    # Note: electron_hops are already updated and pruned in Step 3 above.

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
    # TCA cycle, NADH/FADH2 reactions, and other metabolism constantly
    # produce H+ in matrix. Faster rate so the matrix pool stays visibly
    # populated (pumping + CIV water formation consume matrix H+ quickly).
    metabolic_interval = max(1, int(2 / flux))
    if f % metabolic_interval == 0 and len(sim.matrix_protons) < MATRIX_PROTON_CAP:
        sim.matrix_protons.append(MatrixProton(
            random.randint(SIM_X + 40, WIDTH - 100),
            random.randint(MATRIX_TOP + 30, HEIGHT - 30)))

    # Decay complex active timers
    for k in sim.complex_active:
        if sim.complex_active[k] > 0:
            sim.complex_active[k] -= 1

    # --- Narrative events ---
    sim.update_narrative()

    sim.frame += 1


def _pump_protons(complex_key, count):
    """Consume protons from the matrix pool and pump them UP THROUGH the
       complex into the IMS. The PumpingProton starts at the CONSUMED
       matrix proton's actual position (so students see matrix H+ entering
       the complex from below) and rises through the complex body into
       the IMS."""
    cx = CX[complex_key]
    for _ in range(count):
        start_x = None
        start_y = None
        if sim.matrix_protons:
            # Pick the closest matrix proton to the complex's x
            best_idx = 0
            best_dist = 99999
            for i, mp in enumerate(sim.matrix_protons):
                d = abs(mp.x - cx)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            consumed = sim.matrix_protons.pop(best_idx)
            start_x = consumed.x
            start_y = consumed.y

        # Fallback if no matrix proton was available (shouldn't happen at
        # steady state but keeps the pump running visually)
        if start_x is None:
            start_x = cx + random.uniform(-10, 10)
            start_y = MATRIX_TOP + random.uniform(20, 60)

        # Randomize target_x across the complex width so rising protons
        # fan out instead of lining up in a single column.
        target_x = cx + random.uniform(-14, 14)
        target_y = 30 + random.random() * (IMS_BOTTOM - 60)
        p = PumpingProton(start_x, start_y, target_x, target_y)
        sim.pumping_protons.append(p)


def _consume_matrix_protons_for_water(complex_key, count):
    """CIV consumes matrix H+ that will combine with O2 to form H2O.
       The water particle itself is spawned by the ElectronDescent visual
       when the electron reaches the matrix side of CIV."""
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

    # CoQ and CytC stations (drawn after complexes, on top of the membrane)
    draw_coq_station(screen, pulse=sim.coq_station_pulse)
    draw_cytc_station(screen, pulse=sim.cytc_station_pulse)

    # Persistent H+ population above ATP synthase — a broad decorative
    # cloud filling the IMS column above CV, plus a tighter cluster at
    # the channel entry that feeds the descending InfluxProtons.
    if not sim.blocked["CV"] and not sim.transport_blocked:
        cx_cv = CX["CV"]
        cy_cv = IMS_BOTTOM - 42
        t = sim.frame * 0.04
        # Wider H+ cloud spread through the IMS column above CV
        cloud_positions = [
            (-34, -180), (-18, -165), (6, -190), (24, -170), (38, -155),
            (-28, -135), (-6, -145), (14, -130), (30, -128),
            (-32, -100), (-12, -108), (8, -95), (26, -110), (40, -90),
            (-22, -70), (-2, -80), (18, -65), (34, -72),
            (-28, -40), (-8, -48), (12, -38), (28, -42),
        ]
        for i, (dx, dy) in enumerate(cloud_positions):
            wob_x = math.sin(t * 0.9 + i * 0.4) * 1.8
            wob_y = math.cos(t * 1.0 + i * 0.3) * 1.8
            pygame.draw.circle(
                screen, PROTON_COLOR,
                (int(cx_cv + dx + wob_x), int(cy_cv + dy + wob_y)), 3)
        # Tighter cluster right at the channel entry (source of InfluxProtons)
        for i, (dx, dy) in enumerate([
            (-22, -6), (-10, -16), (2, -2), (12, -14),
            (22, -8), (-16, 6), (16, 4), (0, -26),
        ]):
            wob_x = math.sin(t + i * 0.7) * 1.4
            wob_y = math.cos(t * 1.15 + i * 0.5) * 1.4
            pygame.draw.circle(
                screen, PROTON_COLOR,
                (int(cx_cv + dx + wob_x), int(cy_cv + dy + wob_y)), 3)

    # O2 final electron acceptor at CIV's matrix face
    sim.oxygen_acceptor.draw(screen)

    # Parked electrons at stations (when downstream is blocked)
    for i, p in enumerate(sim.parked_at_coq):
        offset_x = math.cos(p["wobble"]) * 18
        offset_y = math.sin(p["wobble"]) * 10 - 22 - (i // 4) * 14
        px = COQ_STATION_X + offset_x
        py = COQ_STATION_Y + offset_y
        _draw_electron_payload(screen, px, py)
    for i, p in enumerate(sim.parked_at_cytc):
        offset_x = math.cos(p["wobble"]) * 18
        offset_y = math.sin(p["wobble"]) * 10 - 22 - (i // 4) * 14
        px = CYTC_STATION_X + offset_x
        py = CYTC_STATION_Y + offset_y
        _draw_electron_payload(screen, px, py)

    # Partial block indicator
    if sim.partial_block.get("CI"):
        txt = FONT_TINY.render("PARTIAL INHIBITION", True, (255, 200, 50))
        screen.blit(txt, (CX["CI"] - txt.get_width() // 2, MEMBRANE_Y + 78))

    # Electron backup labels near stations
    if sim.stuck_cytc_count > 0:
        txt = FONT_TINY.render(
            f"e\u207b backup ({sim.stuck_cytc_count} parked at Cyt c)",
            True, (255, 100, 100))
        screen.blit(txt, (CYTC_STATION_X - txt.get_width() // 2, COQ_STATION_Y - 60))
    if sim.stuck_coq_count > 0:
        txt = FONT_TINY.render(
            f"e\u207b backup ({sim.stuck_coq_count} parked at CoQ)",
            True, (255, 100, 100))
        screen.blit(txt, (COQ_STATION_X - txt.get_width() // 2, COQ_STATION_Y - 60))

    # (skull image is drawn by _draw_block_x inside each complex's draw function)

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

    # Substrate entries (NADH/FADH2 feeding into CI/CII)
    for se in sim.substrate_entries:
        se.draw(screen)

    # Electron handoff sparkles at CIII
    for eh in sim.electron_handoffs:
        eh.draw(screen)

    # Electron descent through CIV into water
    for ed in sim.electron_descents:
        ed.draw(screen)

    # Electron hops between complexes and CoQ/CytC stations
    for h in sim.electron_hops:
        h.draw(screen)

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

    # Narrative event text - left-aligned, numbered, one fitted box around all
    if sim.narrative_events:
        # Render all lines first to find the widest one
        rendered = []
        max_w = 0
        for i, evt in enumerate(sim.narrative_events):
            alpha = min(255, evt["age"] * 10)
            label = f"{i + 1}. {evt['text']}"
            txt = FONT_MD.render(label, True, evt["color"])
            txt.set_alpha(alpha)
            rendered.append((txt, evt["y_pos"], alpha))
            if txt.get_width() > max_w:
                max_w = txt.get_width()

        # Draw one background box that fits all statements
        first_y = rendered[0][1]
        last_y = rendered[-1][1]
        box_x = SIM_X + 8
        box_y = first_y - 6
        box_w = max_w + 24
        box_h = (last_y - first_y) + 30
        bg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 190))
        screen.blit(bg_surf, (box_x, box_y))

        # Draw each line
        for txt, y_pos, alpha in rendered:
            screen.blit(txt, (box_x + 10, y_pos))

    # Blinking toxin alert - large skull over the target complex
    if sim.toxin_alert_name:
        t = sim.toxin_alert_timer
        blink_cycle = t % 60
        blink_on = blink_cycle < 40

        if blink_on:
            # Position over the target complex
            target = sim.toxin_alert_target
            if target in CX:
                alert_cx = CX[target]
                alert_cy = MEMBRANE_Y if target != "CII" else MEMBRANE_Y + 50
            elif target == "membrane":
                alert_cx = SIM_X + SIM_W // 2
                alert_cy = MEMBRANE_Y
            elif target == "ANT":
                alert_cx = CX["CV"] - 80
                alert_cy = MEMBRANE_Y
            else:
                alert_cx = SIM_X + SIM_W // 2
                alert_cy = MEMBRANE_Y

            # Draw large skull programmatically
            _draw_skull(screen, alert_cx, alert_cy - 50, size=40, color=(255, 50, 50))

            # Chemical short name below skull
            name_txt = FONT_XL.render(sim.toxin_alert_name, True, (255, 60, 60))
            screen.blit(name_txt, (alert_cx - name_txt.get_width() // 2, alert_cy + 30))

            # Full name below that
            full_txt = FONT_SM.render(sim.toxin_alert_full, True, (255, 150, 150))
            screen.blit(full_txt, (alert_cx - full_txt.get_width() // 2, alert_cy + 58))

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
    subtitle = FONT_TINY.render("Click to apply/remove \u2022 Right-click for info", True, LABEL_DIM)
    surf.blit(subtitle, (15, 42))
    pygame.draw.line(surf, (60, 60, 80), (10, 60), (SIDEBAR_W - 10, 60))

    list_y_start = 70
    item_h = 52
    visible_h = HEIGHT - list_y_start - 130
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

    btn_y = HEIGHT - 120
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
    knob_x = slider_rect.x + int((sim.flux / 2.0) * slider_rect.w)
    pygame.draw.circle(surf, ACCENT, (knob_x, slider_rect.y + 6), 8)

    # Request / comment block
    req_y = slider_y + 36
    pygame.draw.line(surf, (60, 60, 80), (10, req_y), (SIDEBAR_W - 10, req_y))
    req_y += 5
    req_txt1 = FONT_TINY.render("Comment or request a chemical addition:", True, (140, 140, 140))
    surf.blit(req_txt1, (10, req_y)); req_y += 15
    email_txt = FONT_TINY.render("support@womenadrift.com", True, (80, 180, 255))
    surf.blit(email_txt, (10, req_y))
    # Underline the email
    pygame.draw.line(surf, (80, 180, 255), (10, req_y + 12), (10 + email_txt.get_width(), req_y + 12), 1)
    # Store email rect for click detection
    sim.email_rect = pygame.Rect(10, req_y, email_txt.get_width(), 14)

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

    pw, ph = SIDEBAR_W - 10, HEIGHT - 20
    px = 5
    py = 10
    sim.info_panel_rect = pygame.Rect(px, py, pw, ph)

    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    pygame.draw.rect(panel, (30, 30, 45, 240), (0, 0, pw, ph), border_radius=12)
    pygame.draw.rect(panel, ACCENT, (0, 0, pw, ph), 1, border_radius=12)

    info = sim.info_panel
    y = 15

    # Title - wrap if it clips the panel width
    title_text = info.get("name", "")
    title_lines = wrap_text(title_text, FONT_XL, pw - 30)
    for line in title_lines:
        title_surf = FONT_XL.render(line, True, ACCENT)
        panel.blit(title_surf, (15, y))
        y += 32

    y += 3


    # Target - bold, larger font, full name
    target_display = {
        "CI": "Complex I", "CII": "Complex II", "CIII": "Complex III",
        "CIV": "Complex IV", "CV": "Complex V", "membrane": "Membrane",
        "ANT": "Adenine Nucleotide Translocase",
    }
    target_val = target_display.get(info.get('target', ''), info.get('target', 'N/A'))
    target_label = FONT_TARGET.render(f"Target: {target_val}", True, (255, 255, 255))
    panel.blit(target_label, (15, y)); y += 30

    # ATP Reduction - larger, bold, bright red
    if "atp_reduction_pct" in info:
        pct = info['atp_reduction_pct']
        atp_txt = FONT_ATP_RED.render(f"ATP Reduction: ~{pct}%", True, (255, 50, 50))
        panel.blit(atp_txt, (15, y)); y += 30

    pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 10

    for line in wrap_text(info.get("description", ""), FONT_SM, pw - 30):
        if y > ph - 70:
            break
        panel.blit(FONT_SM.render(line, True, TEXT_COLOR), (15, y)); y += 18

    y += 5
    sim.ref_link_rect = None
    if "reference_url" in info and y < ph - 50:
        pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 8
        panel.blit(FONT_TITLE.render("Reference:", True, (100, 200, 255)), (15, y)); y += 20

        # Clickable link - underlined, blue, with hover cursor hint
        link_txt = FONT_SM.render(info["reference_url"], True, (80, 180, 255))
        link_lines = wrap_text(info["reference_url"], FONT_SM, pw - 30)
        link_y_start = y
        for line in link_lines:
            if y > ph - 40:
                break
            ltxt = FONT_SM.render(line, True, (80, 180, 255))
            panel.blit(ltxt, (15, y))
            # Underline
            pygame.draw.line(panel, (80, 180, 255), (15, y + ltxt.get_height()),
                             (15 + ltxt.get_width(), y + ltxt.get_height()), 1)
            y += 17

        # Store the clickable area in screen coordinates (panel is at px, py)
        link_h = y - link_y_start
        sim.ref_link_rect = pygame.Rect(px + 15, py + link_y_start, pw - 30, link_h)
        sim.ref_link_url = info["reference_url"]

        y += 4
        click_hint = FONT_TINY.render("Click link to open in browser", True, (120, 160, 200))
        panel.blit(click_hint, (15, y)); y += 15

    # Overview section
    if "overview" in info and y < ph - 60:
        y += 3
        pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 8
        panel.blit(FONT_TITLE.render("Overview:", True, (180, 220, 130)), (15, y)); y += 20
        for line in wrap_text(info["overview"], FONT_SM, pw - 30):
            if y > ph - 30:
                break
            panel.blit(FONT_SM.render(line, True, (200, 220, 180)), (15, y)); y += 17

    # Carcinogenicity section (only shown if data exists)
    if "carcinogenicity" in info and y < ph - 50:
        y += 3
        pygame.draw.line(panel, (80, 80, 100), (15, y), (pw - 15, y)); y += 8
        panel.blit(FONT_TITLE.render("Carcinogenicity:", True, (255, 160, 80)), (15, y)); y += 20
        for line in wrap_text(info["carcinogenicity"], FONT_SM, pw - 30):
            if y > ph - 30:
                break
            panel.blit(FONT_SM.render(line, True, (230, 190, 150)), (15, y)); y += 17

    close_txt = FONT_SM.render("Click outside or press ESC to close", True, LABEL_DIM)
    panel.blit(close_txt, (pw // 2 - close_txt.get_width() // 2, ph - 22))
    surf.blit(panel, (px, py))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def draw_hud(surf):
    # Active effects (top right, no box)
    if sim.active_chemicals:
        acy = 15
        surf.blit(FONT_TITLE.render("Active Effects:", True, (255, 150, 150)), (WIDTH - 220, acy))
        acy += 20
        for chem in sim.active_chemicals:
            surf.blit(FONT_SM.render(f"\u2022 {chem['name']}", True, (255, 180, 180)), (WIDTH - 215, acy))
            acy += 17

    # Title - centered at top of simulation area
    title_txt = FONT_XL.render("Mitochondrial Electron Transport Chain Simulation", True, (200, 200, 200))
    title_x = SIM_X + (SIM_W - title_txt.get_width()) // 2
    surf.blit(title_txt, (title_x, 8))

    # Legend (reflects the current station-based sim)
    leg_y = HEIGHT - 130
    leg_x = WIDTH - 220
    draw_rounded_rect(surf, (0, 0, 0), (leg_x - 10, leg_y - 5, 220, 125), 6, alpha=160)

    # Proton
    pygame.draw.circle(surf, PROTON_COLOR, (leg_x, leg_y + 8), 4)
    surf.blit(FONT_SM.render("Proton (H\u207a)", True, TEXT_COLOR), (leg_x + 14, leg_y))

    # Electron (the glowing yellow traveling dot)
    _draw_electron_payload(surf, leg_x, leg_y + 28)
    surf.blit(FONT_SM.render("Electron (e\u207b)", True, TEXT_COLOR), (leg_x + 14, leg_y + 21))

    # CoQ station sample
    coq_rect = pygame.Rect(leg_x - 14, leg_y + 44, 28, 14)
    pygame.draw.rect(surf, (55, 35, 18), coq_rect, border_radius=7)
    pygame.draw.rect(surf, COQ_ORANGE, coq_rect, 1, border_radius=7)
    coq_lbl = FONT_TINY.render("CoQ", True, (255, 200, 120))
    surf.blit(coq_lbl, (leg_x - coq_lbl.get_width() // 2, leg_y + 45))
    surf.blit(FONT_SM.render("Ubiquinone (CoQ)", True, TEXT_COLOR), (leg_x + 14, leg_y + 43))

    # CytC station sample
    cytc_rect = pygame.Rect(leg_x - 14, leg_y + 66, 28, 14)
    pygame.draw.rect(surf, (22, 30, 55), cytc_rect, border_radius=7)
    pygame.draw.rect(surf, CYTC_BLUE_LIGHT, cytc_rect, 1, border_radius=7)
    cc_lbl = FONT_TINY.render("Cyt c", True, (160, 190, 235))
    surf.blit(cc_lbl, (leg_x - cc_lbl.get_width() // 2, leg_y + 67))
    surf.blit(FONT_SM.render("Cytochrome c", True, TEXT_COLOR), (leg_x + 14, leg_y + 65))

    # ATP
    surf.blit(FONT_SM.render("ATP", True, ATP_COLOR), (leg_x - 10, leg_y + 85))
    surf.blit(FONT_SM.render("= synthesized ATP", True, TEXT_COLOR), (leg_x + 20, leg_y + 85))

    # Water
    water_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
    pygame.draw.circle(water_surf, (80, 160, 255), (7, 7), 5)
    pygame.draw.polygon(water_surf, (80, 160, 255), [(7, 0), (3, 5), (11, 5)])
    surf.blit(water_surf, (leg_x - 7, leg_y + 100))
    surf.blit(FONT_SM.render("Water (H\u2082O) from CIV", True, TEXT_COLOR), (leg_x + 14, leg_y + 105))

    # Bottom disclaimer
    disclaimer_lines = [
        "This simulation is for educational purposes only and is a simplified model of mitochondrial function.",
        "It does not represent the full complexity of biological systems or predict real-world physiological responses.",
        "Information presented should not be used for medical, clinical, or toxicological decision-making.",
        "The creators assume no liability for any use or interpretation of this content.  @womenadrift.com",
    ]
    bot_y = HEIGHT - len(disclaimer_lines) * 13 - 4
    for line in disclaimer_lines:
        dtxt = FONT_TINY.render(line, True, (90, 90, 90))
        surf.blit(dtxt, (SIM_X + (SIM_W - dtxt.get_width()) // 2, bot_y))
        bot_y += 13


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
                        # Check if clicking the reference link
                        if sim.ref_link_rect and sim.ref_link_rect.collidepoint(mx, my):
                            webbrowser.open(sim.ref_link_url)
                            continue
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
                                sim.apply_chemical(chem)
                                sim.info_panel = chem
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

            elif event.type == pygame.MOUSEMOTION:
                if dragging_slider and "slider" in ui:
                    sr = ui["slider"]
                    rel = (mx - sr.x) / sr.w
                    # Slider range 0 to 2; internal clamp at 0.05 minimum so
                    # interval divisions in sim_update stay finite (at 0.05 the
                    # chain is effectively frozen without zero-division errors).
                    sim.flux = max(0.05, min(2.0, rel * 2.0))

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
