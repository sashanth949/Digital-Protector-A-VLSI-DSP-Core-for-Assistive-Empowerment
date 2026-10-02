"""
Adaptive Communication Dashboard - pygame visualizer + serial bridge

Combines the TX <-> laptop <-> RX Pico bridge logic (bridge.py) with a live
pygame UI that mirrors the reference dashboard: a TRANSMITTER panel (raw
noisy wave), a RECEIVER panel (filtered wave + quality), and a control
panel for AUTO / MANUAL mode and filter selection.

Setup:
    pip install pygame pyserial
    python dashboard.py --list      (shows your COM ports)

Edit TX_PORT / RX_PORT below, close Thonny, then run:
    python dashboard.py
"""

import math
import random
import sys
import threading
import time

import pygame
import serial
from serial.tools import list_ports

# --------------------------------------------------------------------------
# SETTINGS
# --------------------------------------------------------------------------
TX_PORT = "COM3"        # transmitter Pico
RX_PORT = "COM4"        # receiver Pico
BAUD = 115200
SEND_INTERVAL = 0.25     # seconds between updates to the receiver

WIDTH, HEIGHT = 900, 620
FPS = 60

# --------------------------------------------------------------------------
# COLORS
# --------------------------------------------------------------------------
BG = (10, 12, 20)
TX_PANEL = (18, 22, 55)
RX_PANEL = (10, 46, 34)
CTRL_PANEL = (24, 24, 28)
WAVE_COLOR = (60, 220, 220)
WHITE = (235, 235, 240)
GREY = (150, 150, 160)
GREEN = (46, 204, 113)
RED = (220, 70, 70)
BTN_BORDER = (90, 90, 100)

FILTERS = ["AVG", "MEDIAN", "LOWPASS"]
FILTER_LABELS = {"AVG": "MOV AVG", "MEDIAN": "MEDIAN", "LOWPASS": "LOW PASS"}


def pick_filter(noise):
    """Same AUTO rule as bridge.py."""
    if noise < 25:
        return "LOWPASS"
    if noise < 60:
        return "AVG"
    return "MEDIAN"


def quality_for(noise):
    return max(0, 100 - noise)


# --------------------------------------------------------------------------
# SHARED STATE
# --------------------------------------------------------------------------
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.noise = 0
        self.count = 0
        self.mode = "AUTO"        # "AUTO" or "MANUAL"
        self.manual_filter = "AVG"
        self.filter = "LOWPASS"
        self.quality = 100
        self.connected = False

    def snapshot(self):
        with self.lock:
            return dict(
                noise=self.noise, count=self.count, mode=self.mode,
                manual_filter=self.manual_filter, filter=self.filter,
                quality=self.quality, connected=self.connected,
            )


state = State()
stop_flag = threading.Event()


# --------------------------------------------------------------------------
# SERIAL THREAD
# --------------------------------------------------------------------------
def serial_worker():
    """Runs the same read-TX / pick-filter / write-RX loop as bridge.py,
    but updates `state` instead of printing to the console."""
    try:
        tx = serial.Serial(TX_PORT, BAUD, timeout=0.2)
        rx = serial.Serial(RX_PORT, BAUD, timeout=0.2)
        with state.lock:
            state.connected = True
        print("Serial bridge connected.")
    except serial.SerialException as e:
        print("Serial error:", e)
        print("Dashboard will keep running without live hardware data.")
        return

    last_send = 0.0
    while not stop_flag.is_set():
        raw = tx.readline().decode(errors="ignore").strip()
        if not raw.startswith("TX,"):
            continue
        parts = raw.split(",")
        try:
            noise = int(parts[2])
            count = int(parts[3])
        except (IndexError, ValueError):
            continue

        with state.lock:
            state.noise = noise
            state.count = count
            mode = state.mode
            manual_filter = state.manual_filter

        flt = pick_filter(noise) if mode == "AUTO" else manual_filter
        qual = quality_for(noise)

        with state.lock:
            state.filter = flt
            state.quality = qual

        now = time.time()
        if now - last_send >= SEND_INTERVAL:
            try:
                rx.write("RX,{},{},{}\n".format(mode, flt, noise).encode())
            except serial.SerialException:
                pass
            last_send = now

    try:
        tx.close()
        rx.close()
    except Exception:
        pass


# --------------------------------------------------------------------------
# DRAW HELPERS
# --------------------------------------------------------------------------
def draw_panel(surf, rect, color, radius=14):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def draw_wave(surf, rect, phase, noise, filter_name=None):
    """Reproduces the Pico firmware's exact per-pixel waveform math:
    y = 47 + 9*sin((x+phase)*0.18) + random jitter in [-noise/10, noise/10]
    then, when filter_name is set, runs it through the same recurrence used
    on the RX Pico (AVG / MEDIAN / LOWPASS), and maps the OLED's 32-63 pixel
    range onto this rect. filter_name=None draws the raw TX-side wave.
    """
    x0, y0, w, h = rect
    amp_jitter = int(noise / 10)
    prev1 = prev2 = 47.0          # feedback memory for AVG / LOWPASS
    raw_prev1 = raw_prev2 = 47.0  # raw (unfiltered) history, for MEDIAN only
    points = []

    for x in range(128):
        raw = 47 + 9 * math.sin((x + phase) * 0.18)
        if amp_jitter:
            raw += random.randint(-amp_jitter, amp_jitter)

        if filter_name == "AVG":
            y = (raw + prev1 + prev2) / 3
        elif filter_name == "MEDIAN":
            # Median over raw samples, NOT over previous filtered output —
            # feeding a filter's own output back into a median collapses
            # ("recursive median lock") almost instantly, especially at
            # high noise. Using raw history avoids that flat-lining.
            y = sorted([raw, raw_prev1, raw_prev2])[1]
        elif filter_name == "LOWPASS":
            y = 0.2 * raw + 0.8 * prev1
        else:
            y = raw

        y = max(32, min(63, y))
        raw_prev2 = raw_prev1
        raw_prev1 = raw
        prev2 = prev1
        prev1 = y

        sx = x0 + w * x / 127
        sy = y0 + h * (y - 32) / 31
        points.append((sx, sy))

    if len(points) > 1:
        pygame.draw.aalines(surf, WAVE_COLOR, False, points)


def draw_progress(surf, rect, frac, color):
    x, y, w, h = rect
    pygame.draw.rect(surf, (40, 40, 46), rect, border_radius=h // 2)
    fw = max(h, int(w * max(0.0, min(1.0, frac))))
    pygame.draw.rect(surf, color, (x, y, fw, h), border_radius=h // 2)


def draw_button(surf, rect, label, font, active, hover):
    color = GREEN if active else ((45, 45, 52) if not hover else (60, 60, 68))
    border = GREEN if active else BTN_BORDER
    pygame.draw.rect(surf, color, rect, border_radius=8)
    pygame.draw.rect(surf, border, rect, width=1, border_radius=8)
    txt = font.render(label, True, (10, 20, 15) if active else WHITE)
    surf.blit(txt, txt.get_rect(center=rect.center))


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    if "--list" in sys.argv:
        for p in list_ports.comports():
            print(p.device, "-", p.description)
        return

    threading.Thread(target=serial_worker, daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Adaptive Communication Dashboard")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("segoeui", 26)
    font_h = pygame.font.SysFont("segoeui", 20)
    font_body = pygame.font.SysFont("consolas", 18)
    font_small = pygame.font.SysFont("consolas", 15)
    font_btn = pygame.font.SysFont("segoeui", 16, bold=True)

    tx_rect = pygame.Rect(20, 70, 460, 190)
    rx_rect = pygame.Rect(20, 280, 460, 190)
    ctrl_rect = pygame.Rect(500, 70, 380, 400)

    mode_auto_btn = pygame.Rect(520, 90, 110, 34)
    mode_manual_btn = pygame.Rect(640, 90, 110, 34)
    filter_btns = {
        "AVG": pygame.Rect(520, 140, 340, 34),
        "MEDIAN": pygame.Rect(520, 184, 340, 34),
        "LOWPASS": pygame.Rect(520, 228, 340, 34),
    }

    t0 = time.time()
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if mode_auto_btn.collidepoint(event.pos):
                    with state.lock:
                        state.mode = "AUTO"
                elif mode_manual_btn.collidepoint(event.pos):
                    with state.lock:
                        state.mode = "MANUAL"
                else:
                    for name, r in filter_btns.items():
                        if r.collidepoint(event.pos):
                            with state.lock:
                                state.manual_filter = name
                                if state.mode == "MANUAL":
                                    state.filter = name

        snap = state.snapshot()
        t = time.time() - t0

        screen.fill(BG)
        title = font_title.render("Adaptive Communication Dashboard", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 32)))

        # ---- Transmitter panel (raw noisy wave) ----
        draw_panel(screen, tx_rect, TX_PANEL)
        screen.blit(font_h.render("TRANSMITTER", True, WHITE), (tx_rect.x + 16, tx_rect.y + 14))
        screen.blit(font_body.render("Signal : SINE", True, GREY), (tx_rect.x + 16, tx_rect.y + 50))
        screen.blit(font_body.render("Noise  : {}%".format(snap["noise"]), True, GREY), (tx_rect.x + 16, tx_rect.y + 74))
        screen.blit(font_body.render("Packet : {}".format(snap["count"]), True, GREY), (tx_rect.x + 16, tx_rect.y + 98))
        draw_wave(screen, (tx_rect.x + 190, tx_rect.y + 20, tx_rect.w - 210, tx_rect.h - 40),
                  t, snap["noise"], filter_name=None)
        draw_progress(screen, (tx_rect.x + 16, tx_rect.bottom - 26, tx_rect.w - 32, 10),
                      snap["noise"] / 100.0, RED)

        # ---- Receiver panel (filtered wave) ----
        draw_panel(screen, rx_rect, RX_PANEL)
        screen.blit(font_h.render("RECEIVER", True, WHITE), (rx_rect.x + 16, rx_rect.y + 14))
        screen.blit(font_body.render("Mode   : {}".format(snap["mode"]), True, GREY), (rx_rect.x + 16, rx_rect.y + 50))
        screen.blit(font_body.render("Filter : {}".format(snap["filter"]), True, GREY), (rx_rect.x + 16, rx_rect.y + 74))
        screen.blit(font_body.render("Quality: {}%".format(snap["quality"]), True, GREY), (rx_rect.x + 16, rx_rect.y + 98))
        draw_wave(screen, (rx_rect.x + 190, rx_rect.y + 20, rx_rect.w - 210, rx_rect.h - 40),
                  t, snap["noise"], filter_name=snap["filter"])
        draw_progress(screen, (rx_rect.x + 16, rx_rect.bottom - 26, rx_rect.w - 32, 10),
                      snap["quality"] / 100.0, GREEN)

        # ---- Control panel ----
        draw_panel(screen, ctrl_rect, CTRL_PANEL)
        draw_button(screen, mode_auto_btn, "AUTO", font_btn, snap["mode"] == "AUTO", mode_auto_btn.collidepoint(mouse_pos))
        draw_button(screen, mode_manual_btn, "MANUAL", font_btn, snap["mode"] == "MANUAL", mode_manual_btn.collidepoint(mouse_pos))

        active_filter = snap["filter"] if snap["mode"] == "AUTO" else snap["manual_filter"]
        for name, r in filter_btns.items():
            draw_button(screen, r, FILTER_LABELS[name], font_btn, active_filter == name, r.collidepoint(mouse_pos))

        info_lines = [
            "AUTO selects best filter",
            "Turn TX knob to add noise",
            "RX OLED shows recovered wave",
            "Better filter = higher quality",
        ]
        for i, line in enumerate(info_lines):
            screen.blit(font_small.render(line, True, GREY), (ctrl_rect.x + 20, ctrl_rect.y + 290 + i * 22))

        if not snap["connected"]:
            warn = font_small.render("No serial connection - check COM ports (see --list)", True, RED)
            screen.blit(warn, (20, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(FPS)

    stop_flag.set()
    pygame.quit()


if __name__ == "__main__":
    main()