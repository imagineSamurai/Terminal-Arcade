#!/usr/bin/env python3
"""
TERMINAL ARCADE TUI - CMD Mini-Games Suite
Includes:
  1. Snake (with difficulty speeds, wall/portal modes, bonus fruits & high scores)
  2. Tic-Tac-Toe / XO (1P vs Unbeatable AI, 1P vs Casual AI, 2P Local, big visual board)
  3. 2048 (Full color-coded tile puzzle with Undo & High Score)
  4. Connect Four (1P vs Smart AI or 2P Local with animated drop & win highlight)

Controls:
  Arrow Keys / WASD : Move / Navigate
  Enter / Space     : Select / Place
  1 - 9             : Quick cell/column selection (XO & Connect 4)
  P                 : Pause (Snake)
  R                 : Restart current game
  M / Tab           : Change game mode / difficulty
  Esc / Q           : Back to Main Menu / Quit
"""

import ctypes
import json
import math
import os
import random
import shutil
import sys
import time
from collections import deque

# Windows vs Unix non-blocking input setup
if os.name == "nt":
    import msvcrt
else:
    import select
    import termios
    import tty


# ============================================================================
# ANSI & TERMINAL HELPERS
# ============================================================================

class Style:
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"

    # Foreground colors (bright/vivid)
    FG_BLACK = "\x1b[30m"
    FG_RED = "\x1b[91m"
    FG_GREEN = "\x1b[92m"
    FG_YELLOW = "\x1b[93m"
    FG_BLUE = "\x1b[94m"
    FG_MAGENTA = "\x1b[95m"
    FG_CYAN = "\x1b[96m"
    FG_WHITE = "\x1b[97m"
    FG_GRAY = "\x1b[90m"
    FG_ORANGE = "\x1b[38;5;208m"
    FG_GOLD = "\x1b[38;5;220m"
    FG_PINK = "\x1b[38;5;213m"
    FG_LIME = "\x1b[38;5;118m"
    FG_PURPLE = "\x1b[38;5;141m"

    # Background colors
    BG_DARK = "\x1b[48;5;235m"
    BG_PANEL = "\x1b[48;5;236m"
    BG_SELECT = "\x1b[48;5;24m"
    BG_WIN = "\x1b[48;5;22m"
    BG_ALERT = "\x1b[48;5;52m"


import re
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def visible_len(text: str) -> int:
    """Return visible character length ignoring ANSI escape sequences."""
    return len(ANSI_RE.sub("", text))


def pad_center(text: str, width: int, fill: str = " ") -> str:
    vlen = visible_len(text)
    if vlen >= width:
        return text
    left = (width - vlen) // 2
    right = width - vlen - left
    return (fill * left) + text + (fill * right)


def pad_right(text: str, width: int, fill: str = " ") -> str:
    vlen = visible_len(text)
    if vlen >= width:
        return text
    return text + (fill * (width - vlen))


class Terminal:
    """Handles flicker-free rendering, UTF-8 Windows CMD setup, and non-blocking input."""

    def __init__(self):
        self.old_settings = None
        self.setup_console()

    def setup_console(self):
        if os.name == "nt":
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleTitleW("Retro Terminal Arcade TUI")
                # Set UTF-8 codepage (65001) so box-drawing characters work in cmd.exe
                kernel32.SetConsoleOutputCP(65001)
                kernel32.SetConsoleCP(65001)
                # Enable Virtual Terminal Processing (0x0004) on stdout
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            except Exception:
                pass
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    def enter_tui(self):
        if os.name != "nt":
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        # Enter alternate screen buffer, clear screen, hide cursor
        sys.stdout.write("\x1b[?1049h\x1b[2J\x1b[H\x1b[?25l")
        sys.stdout.flush()

    def exit_tui(self):
        # Show cursor, leave alternate screen buffer, reset style
        sys.stdout.write("\x1b[?25h\x1b[?1049l" + Style.RESET)
        sys.stdout.flush()
        if os.name != "nt" and self.old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_size(self):
        size = shutil.get_terminal_size((80, 28))
        return size.columns, size.lines

    def clear(self):
        sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.flush()

    def render_frame(self, lines: list[str]):
        """Render lines centered in the terminal without flickering."""
        cols, rows = self.get_size()
        content_height = len(lines)
        top_pad = max(0, (rows - content_height) // 2)

        out = ["\x1b[H"]  # Home cursor
        for _ in range(top_pad):
            out.append("\x1b[K\n")

        for idx, line in enumerate(lines):
            if top_pad + idx >= rows - 1:
                break
            vlen = visible_len(line)
            left_pad = max(0, (cols - vlen) // 2)
            out.append((" " * left_pad) + line + Style.RESET + "\x1b[K\n")

        # Clear remaining lines below
        remaining = rows - 1 - (top_pad + len(lines))
        for _ in range(max(0, remaining)):
            out.append("\x1b[K\n")

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def get_key(self) -> str | None:
        """Non-blocking key reader returning normalized key names."""
        if os.name == "nt":
            if not msvcrt.kbhit():
                return None
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):
                if msvcrt.kbhit():
                    ch2 = msvcrt.getch()
                else:
                    ch2 = msvcrt.getch()
                mapping = {
                    b"H": "UP",
                    b"P": "DOWN",
                    b"K": "LEFT",
                    b"M": "RIGHT",
                    b"G": "HOME",
                    b"O": "END",
                }
                return mapping.get(ch2, None)
            if ch == b"\r":
                return "ENTER"
            if ch == b"\x1b":
                return "ESC"
            if ch == b"\t":
                return "TAB"
            if ch == b" ":
                return "SPACE"
            if ch == b"\x08":
                return "BACKSPACE"
            if ch == b"\x03":
                raise KeyboardInterrupt
            try:
                decoded = ch.decode("utf-8", errors="ignore").upper()
                if decoded == "W":
                    return "UP"
                if decoded == "S":
                    return "DOWN"
                if decoded == "A":
                    return "LEFT"
                if decoded == "D":
                    return "RIGHT"
                return decoded
            except Exception:
                return None
        else:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if not dr:
                return None
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                dr2, _, _ = select.select([sys.stdin], [], [], 0.01)
                if dr2:
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        return {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}.get(ch3, "ESC")
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == "\t":
                return "TAB"
            if ch == " ":
                return "SPACE"
            upper = ch.upper()
            if upper == "W":
                return "UP"
            if upper == "S":
                return "DOWN"
            if upper == "A":
                return "LEFT"
            if upper == "D":
                return "RIGHT"
            return upper

    VK_MAP = {
        "UP": 0x26,
        "DOWN": 0x28,
        "LEFT": 0x25,
        "RIGHT": 0x27,
        "W": 0x57,
        "S": 0x53,
        "A": 0x41,
        "D": 0x44,
        "SPACE": 0x20,
        "Z": 0x5A,
        "X": 0x58,
        "C": 0x43,
        "SHIFT": 0x10,
        "LSHIFT": 0xA0,
        "RSHIFT": 0xA1,
    }

    def is_key_down(self, key_name: str) -> bool:
        """Check if a physical key is currently held down (Windows GetAsyncKeyState)."""
        if os.name != "nt":
            return False
        if key_name == "SHIFT":
            try:
                u32 = ctypes.windll.user32
                return bool(
                    (u32.GetAsyncKeyState(0x10) & 0x8000)
                    or (u32.GetAsyncKeyState(0xA0) & 0x8000)
                    or (u32.GetAsyncKeyState(0xA1) & 0x8000)
                )
            except Exception:
                return False
        vk = self.VK_MAP.get(key_name)
        if vk is None:
            return False
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            return False


# ============================================================================
# SCOREBOARD PERSISTENCE
# ============================================================================

if os.environ.get("ARCADE_EXECUTABLE"):
    EXECUTABLE_PATH = os.path.abspath(os.environ["ARCADE_EXECUTABLE"])
    BASE_DIR = os.path.dirname(EXECUTABLE_PATH)
elif getattr(sys, "frozen", False):
    EXECUTABLE_PATH = os.path.abspath(sys.executable)
    BASE_DIR = os.path.dirname(EXECUTABLE_PATH)
else:
    EXECUTABLE_PATH = os.path.abspath(__file__)
    BASE_DIR = os.path.dirname(EXECUTABLE_PATH)

SCORE_FILE = os.path.join(BASE_DIR, "arcade_scores.json")
if not os.access(BASE_DIR, os.W_OK) and not (os.path.exists(SCORE_FILE) and os.access(SCORE_FILE, os.W_OK)):
    SCORE_FILE = os.path.expanduser("~/.arcade_scores.json")


def is_in_path() -> bool:
    """Check whether Terminal Arcade is already available in the user's PATH."""
    if os.name == "nt":
        target = os.path.normcase(os.path.normpath(BASE_DIR))
        env_dirs = [
            os.path.normcase(os.path.normpath(p.strip()))
            for p in os.environ.get("PATH", "").split(";")
            if p.strip()
        ]
        if target in env_dirs:
            return True
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
                reg_dirs = [
                    os.path.normcase(os.path.normpath(p.strip()))
                    for p in user_path.split(";")
                    if p.strip()
                ]
                if target in reg_dirs:
                    return True
        except Exception:
            pass
        return False
    else:
        target = os.path.normpath(BASE_DIR)
        env_dirs = [os.path.normpath(p.strip()) for p in os.environ.get("PATH", "").split(":") if p.strip()]
        if target in env_dirs:
            return True
        found = shutil.which("arcade")
        if found and os.path.exists(found):
            try:
                if os.path.samefile(found, EXECUTABLE_PATH):
                    return True
            except Exception:
                pass
        return False


def add_to_path() -> tuple[bool, str]:
    """Add Terminal Arcade to the user's PATH on Windows or Linux/macOS."""
    if os.name == "nt":
        try:
            # If the release binary is named e.g. terminal-arcade_3.0.0_x64.exe,
            # ensure an arcade.bat wrapper exists next to it so `arcade` works in CMD/PowerShell.
            exe_name = os.path.basename(EXECUTABLE_PATH)
            if exe_name.lower() not in ("arcade.exe", "arcade.py"):
                bat_shim = os.path.join(BASE_DIR, "arcade.bat")
                with open(bat_shim, "w", encoding="utf-8") as bf:
                    bf.write(f'@echo off\n"%~dp0{exe_name}" %*\n')

            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE
            ) as key:
                try:
                    current_path, reg_type = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current_path, reg_type = "", winreg.REG_EXPAND_SZ

                parts = [p.strip() for p in current_path.split(";") if p.strip()]
                norm_parts = [os.path.normcase(os.path.normpath(p)) for p in parts]
                target_norm = os.path.normcase(os.path.normpath(BASE_DIR))

                if target_norm not in norm_parts:
                    parts.append(BASE_DIR)
                    new_path = ";".join(parts)
                    winreg.SetValueEx(key, "Path", 0, reg_type, new_path)

            # Broadcast WM_SETTINGCHANGE so new terminals pick up the updated PATH immediately
            try:
                result = ctypes.c_ulong()
                ctypes.windll.user32.SendMessageTimeoutW(
                    0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(result)
                )
            except Exception:
                pass

            os.environ["PATH"] = BASE_DIR + ";" + os.environ.get("PATH", "")
            return (
                True,
                f"Added '{BASE_DIR}' to your Windows User PATH.\n"
                f"  You can now run 'arcade' (or 'arcade snake', 'arcade shmup', etc.) from any terminal!",
            )
        except Exception as exc:
            return False, f"Failed to update Windows PATH: {exc}"
    else:
        try:
            # Ensure the ELF binary / script has executable permissions
            try:
                st = os.stat(EXECUTABLE_PATH)
                os.chmod(EXECUTABLE_PATH, st.st_mode | 0o111)
            except Exception:
                pass

            # 1. Symlink into ~/.local/bin/arcade
            local_bin = os.path.expanduser("~/.local/bin")
            os.makedirs(local_bin, exist_ok=True)
            link_path = os.path.join(local_bin, "arcade")
            if os.path.abspath(EXECUTABLE_PATH) != os.path.abspath(link_path):
                if os.path.lexists(link_path):
                    os.remove(link_path)
                os.symlink(EXECUTABLE_PATH, link_path)

            # 2. Ensure BASE_DIR and ~/.local/bin are exported in user shell profiles
            export_line = f'export PATH="$PATH:{BASE_DIR}:$HOME/.local/bin"'
            rc_candidates = [
                os.path.expanduser("~/.bashrc"),
                os.path.expanduser("~/.zshrc"),
                os.path.expanduser("~/.profile"),
            ]
            updated_files = []
            existing_rcs = [p for p in rc_candidates if os.path.exists(p)]
            if not existing_rcs:
                existing_rcs = [os.path.expanduser("~/.bashrc"), os.path.expanduser("~/.profile")]

            for rc_file in existing_rcs:
                try:
                    content = ""
                    if os.path.exists(rc_file):
                        with open(rc_file, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    if BASE_DIR not in content:
                        with open(rc_file, "a", encoding="utf-8") as f:
                            if content and not content.endswith("\n"):
                                f.write("\n")
                            f.write(f"\n# Terminal Arcade PATH\n{export_line}\n")
                        updated_files.append(os.path.basename(rc_file))
                except Exception:
                    pass

            os.environ["PATH"] = f"{BASE_DIR}:{local_bin}:" + os.environ.get("PATH", "")
            rc_note = f" (updated {', '.join(updated_files)})" if updated_files else ""
            return (
                True,
                f"Installed symlink '{link_path}' -> '{EXECUTABLE_PATH}'{rc_note}.\n"
                f"  You can now run 'arcade' (or 'arcade snake', 'arcade shmup', etc.) from anywhere in the terminal!",
            )
        except Exception as exc:
            return False, f"Failed to update Linux PATH: {exc}"


def prompt_path_install(scores: dict, force: bool = False):
    """Optionally ask the user whether they want to add Terminal Arcade to PATH."""
    if not force:
        if scores.get("path_prompt_done", False) or is_in_path():
            return
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return

    platform_label = "Windows (arcade.exe)" if os.name == "nt" else "Linux (arcade ELF)"
    print(f"\n{Style.FG_CYAN}╔════════════════════════════════════════════════════════════════════════╗{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}  {Style.FG_GOLD}{Style.BOLD}★  OPTIONAL INSTALLATION: ADD TERMINAL ARCADE TO PATH  ★{Style.RESET}              {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}╠════════════════════════════════════════════════════════════════════════╣{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}  Platform : {Style.FG_WHITE}{platform_label:<58}{Style.RESET} {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}  Location : {Style.FG_GRAY}{BASE_DIR[:58]:<58}{Style.RESET} {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}                                                                        {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}  Adding {Style.FG_GREEN}arcade{Style.RESET} to your PATH lets you launch it from anywhere in        {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}║{Style.RESET}  the terminal (e.g. {Style.FG_YELLOW}arcade{Style.RESET}, {Style.FG_YELLOW}arcade snake{Style.RESET}, {Style.FG_YELLOW}arcade shmup{Style.RESET}).               {Style.FG_CYAN}║{Style.RESET}")
    print(f"{Style.FG_CYAN}╚════════════════════════════════════════════════════════════════════════╝{Style.RESET}")

    try:
        ans = input(f"{Style.FG_YELLOW}Would you like to add Terminal Arcade to your PATH? [y/N]: {Style.RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        ans = "n"

    scores["path_prompt_done"] = True
    save_scores(scores)

    if ans in ("y", "yes"):
        ok, msg = add_to_path()
        color = Style.FG_GREEN if ok else Style.FG_RED
        prefix = "✔" if ok else "✖"
        print(f"\n  {color}{Style.BOLD}{prefix} {msg}{Style.RESET}\n")
        if not force:
            try:
                input(f"  {Style.FG_GRAY}Press Enter to launch Terminal Arcade...{Style.RESET}")
            except (EOFError, KeyboardInterrupt):
                pass
    else:
        print(
            f"\n  {Style.FG_GRAY}Skipped PATH setup. (Run 'arcade --install' anytime to add it later.){Style.RESET}\n"
        )
        if not force:
            time.sleep(0.6)


def load_scores() -> dict:
    default = {
        "snake_high": 0,
        "snake_games": 0,
        "xo_x_wins": 0,
        "xo_o_wins": 0,
        "xo_draws": 0,
        "pong_p1_wins": 0,
        "pong_p2_wins": 0,
        "pong_best_rally": 0,
        "shmup_high": 0,
        "shmup_max_wave": 1,
        "cyberwing_high": 0,
        "arena_shmup_high": 0,
        "bricks_high": 0,
        "game_2048_high": 0,
        "c4_p1_wins": 0,
        "c4_p2_wins": 0,
        "path_prompt_done": False,
    }
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default.update(data)
        except Exception:
            pass
    return default


def save_scores(scores: dict):
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    except Exception:
        pass


# ============================================================================
# UI DRAWING HELPERS
# ============================================================================

def draw_box(title: str, body_lines: list[str], width: int, border_color: str = Style.FG_CYAN) -> list[str]:
    """Wrap body_lines inside a Unicode double/rounded border box of exact visible width."""
    max_body = max((visible_len(l) for l in body_lines), default=0)
    inner_w = max(width - 2, max_body)
    out = []
    if title:
        title_str = f" {title} "
        t_len = visible_len(title_str)
        left_bar = (inner_w - t_len) // 2
        right_bar = inner_w - t_len - left_bar
        out.append(
            f"{border_color}╔{'═' * left_bar}{Style.RESET}{Style.BOLD}{title_str}{Style.RESET}{border_color}{'═' * right_bar}╗{Style.RESET}"
        )
    else:
        out.append(f"{border_color}╔{'═' * inner_w}╗{Style.RESET}")

    for line in body_lines:
        padded = pad_right(line, inner_w)
        out.append(f"{border_color}║{Style.RESET}{padded}{border_color}║{Style.RESET}")

    out.append(f"{border_color}╚{'═' * inner_w}╝{Style.RESET}")
    return out


# ============================================================================
# GAME 1: SNAKE TUI
# ============================================================================

class SnakeGame:
    SPEEDS = [
        ("CHILL", 0.13, Style.FG_GREEN),
        ("NORMAL", 0.09, Style.FG_CYAN),
        ("FAST", 0.06, Style.FG_YELLOW),
        ("INSANE", 0.04, Style.FG_RED),
    ]

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.grid_w = 24
        self.grid_h = 16
        self.speed_idx = 1  # NORMAL
        self.wrap_walls = False
        self.reset()

    def reset(self):
        cx, cy = self.grid_w // 2, self.grid_h // 2
        self.snake = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.direction = (1, 0)
        self.turn_queue = deque()
        self.score = 0
        self.apples_eaten = 0
        self.paused = False
        self.game_over = False
        self.new_record = False
        self.bonus_food = None  # (x, y, expire_tick)
        self.ticks = 0
        self.spawn_food()

    def spawn_food(self):
        occupied = set(self.snake)
        if self.bonus_food:
            occupied.add((self.bonus_food[0], self.bonus_food[1]))
        free = [
            (x, y)
            for x in range(self.grid_w)
            for y in range(self.grid_h)
            if (x, y) not in occupied
        ]
        self.food = random.choice(free) if free else None

    def spawn_bonus(self):
        occupied = set(self.snake)
        if self.food:
            occupied.add(self.food)
        free = [
            (x, y)
            for x in range(self.grid_w)
            for y in range(self.grid_h)
            if (x, y) not in occupied
        ]
        if free:
            bx, by = random.choice(free)
            self.bonus_food = (bx, by, self.ticks + 45)

    def handle_input(self, key: str) -> bool:
        """Returns False if user wants to return to main menu."""
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key == "P" or (key == "SPACE" and not self.game_over):
            self.paused = not self.paused
            return True
        if key in ("ENTER", "SPACE") and self.game_over:
            self.reset()
            return True
        if key == "M":
            self.speed_idx = (self.speed_idx + 1) % len(self.SPEEDS)
            return True
        if key == "TAB":
            self.wrap_walls = not self.wrap_walls
            return True

        dir_map = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0),
        }
        if key in dir_map and not self.paused and not self.game_over:
            new_dir = dir_map[key]
            last_dir = self.turn_queue[-1] if self.turn_queue else self.direction
            # Prevent 180-degree self-reversal
            if (new_dir[0] + last_dir[0], new_dir[1] + last_dir[1]) != (0, 0) and new_dir != last_dir:
                if len(self.turn_queue) < 2:
                    self.turn_queue.append(new_dir)
        return True

    def step(self):
        if self.paused or self.game_over:
            return

        self.ticks += 1
        if self.turn_queue:
            self.direction = self.turn_queue.popleft()

        hx, hy = self.snake[0]
        dx, dy = self.direction
        nx, ny = hx + dx, hy + dy

        if self.wrap_walls:
            nx %= self.grid_w
            ny %= self.grid_h
        else:
            if nx < 0 or nx >= self.grid_w or ny < 0 or ny >= self.grid_h:
                self._trigger_game_over()
                return

        # Check collision with body (excluding tail if it will move this turn)
        body_without_tail = list(self.snake)[:-1]
        if (nx, ny) in body_without_tail:
            self._trigger_game_over()
            return

        self.snake.appendleft((nx, ny))

        # Check food collision
        if self.food and (nx, ny) == self.food:
            speed_mult = self.speed_idx + 1
            self.score += 10 * speed_mult
            self.apples_eaten += 1
            if self.score > self.scores["snake_high"]:
                self.scores["snake_high"] = self.score
                self.new_record = True
                save_scores(self.scores)
            self.spawn_food()
            if self.apples_eaten % 5 == 0 and not self.bonus_food:
                self.spawn_bonus()
        elif self.bonus_food and (nx, ny) == (self.bonus_food[0], self.bonus_food[1]):
            remaining = max(1, self.bonus_food[2] - self.ticks)
            self.score += 25 + remaining
            if self.score > self.scores["snake_high"]:
                self.scores["snake_high"] = self.score
                self.new_record = True
                save_scores(self.scores)
            self.bonus_food = None
            self.snake.pop()
        else:
            self.snake.pop()

        if self.bonus_food and self.ticks >= self.bonus_food[2]:
            self.bonus_food = None

    def _trigger_game_over(self):
        self.game_over = True
        self.scores["snake_games"] = self.scores.get("snake_games", 0) + 1
        save_scores(self.scores)

    def render(self) -> list[str]:
        speed_name, _, speed_col = self.SPEEDS[self.speed_idx]
        wall_label = f"{Style.FG_MAGENTA}PORTAL{Style.RESET}" if self.wrap_walls else f"{Style.FG_CYAN}SOLID{Style.RESET}"

        # Each cell is 2 chars wide so grid is visually square
        board_char_w = self.grid_w * 2
        box_w = 80

        header_stats = (
            f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<6}{Style.RESET}  "
            f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores['snake_high']:<6}{Style.RESET}  "
            f"{Style.BOLD}SPEED:{Style.RESET} {speed_col}{speed_name:<7}{Style.RESET}  "
            f"{Style.BOLD}WALLS:{Style.RESET} {wall_label}"
        )

        body = [pad_center(header_stats, box_w - 2)]

        # Bonus bar if active
        if self.bonus_food:
            rem = max(0, self.bonus_food[2] - self.ticks)
            bar_len = min(20, int((rem / 45) * 20))
            bonus_line = f"{Style.FG_GOLD}★ BONUS FRUIT: [{'█' * bar_len}{'·' * (20 - bar_len)}] {rem}{Style.RESET}"
            body.append(pad_center(bonus_line, box_w - 2))
        else:
            body.append(
                pad_center(f"{Style.DIM}Eat 5 apples to spawn a Golden Bonus Star ★{Style.RESET}", box_w - 2)
            )

        border_col = Style.FG_MAGENTA if self.wrap_walls else Style.FG_CYAN
        h_char = "┄" if self.wrap_walls else "─"
        v_char = "┊" if self.wrap_walls else "│"

        body.append(pad_center(f"{border_col}┌{h_char * board_char_w}┐{Style.RESET}", box_w - 2))

        snake_list = list(self.snake)
        snake_set = set(snake_list[1:])
        head = snake_list[0]

        for y in range(self.grid_h):
            row_cells = []
            for x in range(self.grid_w):
                pos = (x, y)
                if pos == head:
                    col = Style.FG_RED if self.game_over else Style.FG_LIME
                    row_cells.append(f"{col}{Style.BOLD}██{Style.RESET}")
                elif pos in snake_set:
                    idx = snake_list.index(pos)
                    shade = Style.FG_GREEN if idx % 2 == 0 else Style.FG_LIME
                    row_cells.append(f"{shade}▓▓{Style.RESET}")
                elif self.food == pos:
                    row_cells.append(f"{Style.FG_RED}{Style.BOLD}●●{Style.RESET}")
                elif self.bonus_food and (self.bonus_food[0], self.bonus_food[1]) == pos:
                    blink = Style.FG_GOLD if (self.ticks % 2 == 0) else Style.FG_YELLOW
                    row_cells.append(f"{blink}{Style.BOLD}★★{Style.RESET}")
                else:
                    dot = f"{Style.FG_GRAY}· {Style.RESET}" if (x + y) % 2 == 0 else "  "
                    row_cells.append(dot)

            # Overlay status banner in the middle of the field if paused or game over
            row_str = "".join(row_cells)
            if self.game_over and y in (self.grid_h // 2 - 1, self.grid_h // 2, self.grid_h // 2 + 1):
                if y == self.grid_h // 2 - 1:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}   !! GAME OVER! SCORE: {self.score:<5} !!   {Style.RESET}"
                elif y == self.grid_h // 2:
                    rec = " ★ NEW HIGH SCORE! ★ " if self.new_record else " Press [ENTER] or [R] to Replay "
                    msg = f"{Style.BG_ALERT}{Style.FG_GOLD}{Style.BOLD}{rec:^34}{Style.RESET}"
                else:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}      Press [Q/ESC] for Menu      {Style.RESET}"
                row_str = pad_center(msg, board_char_w)
            elif self.paused and y == self.grid_h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, board_char_w)

            body.append(pad_center(f"{border_col}{v_char}{Style.RESET}{row_str}{border_col}{v_char}{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{border_col}└{h_char * board_char_w}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[WASD/Arrows]{Style.RESET} Move  "
            f"{Style.FG_YELLOW}[P]{Style.RESET} Pause  "
            f"{Style.FG_YELLOW}[M]{Style.RESET} Speed  "
            f"{Style.FG_YELLOW}[Tab]{Style.RESET} Walls  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Restart  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ RETRO SNAKE ARCADE ★", body, box_w, Style.FG_GREEN)

    def run(self):
        self.reset()
        last_step = time.perf_counter()
        while True:
            # Drain all pending keys so fast turns work cleanly
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            _, tick_interval, _ = self.SPEEDS[self.speed_idx]
            now = time.perf_counter()
            if now - last_step >= tick_interval:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.015)


# ============================================================================
# GAME 2: TIC-TAC-TOE (XO) TUI
# ============================================================================

class TicTacToeGame:
    MODES = [
        "1P vs AI (Unbeatable)",
        "1P vs AI (Casual)",
        "2P Local (Pass & Play)",
    ]

    WIN_LINES = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Cols
        (0, 4, 8), (2, 4, 6),             # Diagonals
    ]

    # 3-row ASCII art for each cell (width 9 chars)
    ART_X = [
        r"  \   /  ",
        r"    X    ",
        r"  /   \  ",
    ]
    ART_O = [
        r"  ╭───╮  ",
        r"  │   │  ",
        r"  ╰───╯  ",
    ]

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.mode_idx = 0
        self.cursor = 4  # Center cell
        self.human_starts = True
        self.reset()

    def reset(self):
        self.board = [""] * 9
        self.turn = "X" if self.human_starts else "O"
        self.winner = None  # "X", "O", or "DRAW"
        self.win_combo = ()
        if self.mode_idx in (0, 1) and self.turn == "O":
            self.ai_move()

    def check_winner(self, b: list[str]):
        for a, c, d in self.WIN_LINES:
            if b[a] and b[a] == b[c] == b[d]:
                return b[a], (a, c, d)
        if all(cell != "" for cell in b):
            return "DRAW", ()
        return None, ()

    def minimax(self, b: list[str], is_maximizing: bool, depth: int = 0) -> int:
        win, _ = self.check_winner(b)
        if win == "O":
            return 10 - depth
        if win == "X":
            return depth - 10
        if win == "DRAW":
            return 0

        if is_maximizing:
            best = -999
            for i in range(9):
                if b[i] == "":
                    b[i] = "O"
                    best = max(best, self.minimax(b, False, depth + 1))
                    b[i] = ""
            return best
        else:
            best = 999
            for i in range(9):
                if b[i] == "":
                    b[i] = "X"
                    best = min(best, self.minimax(b, True, depth + 1))
                    b[i] = ""
            return best

    def ai_move(self):
        empty = [i for i, v in enumerate(self.board) if v == ""]
        if not empty or self.winner:
            return

        if self.mode_idx == 1 and random.random() < 0.45:
            # Casual AI makes occasional non-optimal moves
            choice = random.choice(empty)
        else:
            # Unbeatable Minimax
            if len(empty) == 9:
                choice = random.choice([0, 2, 4, 6, 8])
            else:
                best_score = -999
                best_moves = []
                for i in empty:
                    self.board[i] = "O"
                    score = self.minimax(self.board, False, 0)
                    self.board[i] = ""
                    if score > best_score:
                        best_score = score
                        best_moves = [i]
                    elif score == best_score:
                        best_moves.append(i)
                choice = random.choice(best_moves)

        self.board[choice] = "O"
        self._after_move()

    def _after_move(self):
        win, combo = self.check_winner(self.board)
        if win:
            self.winner = win
            self.win_combo = combo
            if win == "X":
                self.scores["xo_x_wins"] += 1
            elif win == "O":
                self.scores["xo_o_wins"] += 1
            else:
                self.scores["xo_draws"] += 1
            save_scores(self.scores)
        else:
            self.turn = "O" if self.turn == "X" else "X"

    def make_move(self, idx: int):
        if self.winner or self.board[idx] != "":
            return
        self.board[idx] = self.turn
        self._after_move()
        if not self.winner and self.mode_idx in (0, 1) and self.turn == "O":
            self.ai_move()

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.human_starts = not self.human_starts
            self.reset()
            return True
        if key in ("M", "TAB"):
            self.mode_idx = (self.mode_idx + 1) % len(self.MODES)
            self.reset()
            return True

        if key in "123456789" and len(key) == 1:
            idx = int(key) - 1
            self.cursor = idx
            self.make_move(idx)
            return True

        r, c = divmod(self.cursor, 3)
        if key == "UP":
            r = (r - 1) % 3
        elif key == "DOWN":
            r = (r + 1) % 3
        elif key == "LEFT":
            c = (c - 1) % 3
        elif key == "RIGHT":
            c = (c + 1) % 3
        elif key in ("ENTER", "SPACE"):
            if self.winner:
                self.human_starts = not self.human_starts
                self.reset()
            else:
                self.make_move(self.cursor)
            return True

        self.cursor = r * 3 + c
        return True

    def render(self) -> list[str]:
        box_w = 78
        mode_name = self.MODES[self.mode_idx]
        p2_label = "AI (O)" if self.mode_idx in (0, 1) else "P2 (O)"

        body = [
            pad_center(f"{Style.BOLD}MODE:{Style.RESET} {Style.FG_YELLOW}{mode_name}{Style.RESET}", box_w - 2),
            pad_center(
                f"{Style.FG_CYAN}[X] P1 (X): {self.scores['xo_x_wins']}{Style.RESET}   "
                f"{Style.FG_GRAY}[=] Draws: {self.scores['xo_draws']}{Style.RESET}   "
                f"{Style.FG_PINK}[O] {p2_label}: {self.scores['xo_o_wins']}{Style.RESET}",
                box_w - 2,
            ),
            "",
        ]

        # Build the 3x3 visual grid
        body.append(pad_center(f"{Style.FG_GRAY}┌─────────┬─────────┬─────────┐{Style.RESET}", box_w - 2))
        for grid_r in range(3):
            for sub_r in range(3):
                row_parts = [f"{Style.FG_GRAY}│{Style.RESET}"]
                for grid_c in range(3):
                    idx = grid_r * 3 + grid_c
                    val = self.board[idx]
                    is_cur = (idx == self.cursor and not self.winner)
                    is_win = (idx in self.win_combo)

                    bg = Style.BG_WIN if is_win else (Style.BG_SELECT if is_cur else "")
                    if val == "X":
                        fg = Style.FG_GOLD if is_win else Style.FG_CYAN
                        art = self.ART_X[sub_r]
                        cell_str = f"{bg}{fg}{Style.BOLD}{art}{Style.RESET}"
                    elif val == "O":
                        fg = Style.FG_GOLD if is_win else Style.FG_PINK
                        art = self.ART_O[sub_r]
                        cell_str = f"{bg}{fg}{Style.BOLD}{art}{Style.RESET}"
                    else:
                        if sub_r == 1:
                            hint = f"[{idx + 1}]" if is_cur else f" {idx + 1} "
                            col = Style.FG_WHITE if is_cur else Style.FG_GRAY
                            cell_str = f"{bg}{col}   {hint}   {Style.RESET}"
                        else:
                            cell_str = f"{bg}         {Style.RESET}"

                    row_parts.append(cell_str)
                    row_parts.append(f"{Style.FG_GRAY}│{Style.RESET}")
                body.append(pad_center("".join(row_parts), box_w - 2))

            if grid_r < 2:
                body.append(pad_center(f"{Style.FG_GRAY}├─────────┼─────────┼─────────┤{Style.RESET}", box_w - 2))
        body.append(pad_center(f"{Style.FG_GRAY}└─────────┴─────────┴─────────┘{Style.RESET}", box_w - 2))
        body.append("")

        if self.winner:
            if self.winner == "DRAW":
                status = f"{Style.BG_SELECT}{Style.FG_YELLOW}{Style.BOLD}  === IT'S A DRAW! Press [ENTER/R] for Next Round ===  {Style.RESET}"
            else:
                who = "PLAYER 1 (X)" if self.winner == "X" else (p2_label)
                status = f"{Style.BG_WIN}{Style.FG_GOLD}{Style.BOLD}  ★ {who} WINS! Press [ENTER/R] to Play Again ★  {Style.RESET}"
        else:
            turn_col = Style.FG_CYAN if self.turn == "X" else Style.FG_PINK
            turn_name = "Player 1 (X)" if self.turn == "X" else p2_label
            status = f"Turn: {turn_col}{Style.BOLD}{turn_name}{Style.RESET} — Use Arrows/WASD + Space or Keys [1-9]"

        body.append(pad_center(status, box_w - 2))
        body.append("")
        controls = (
            f"{Style.FG_YELLOW}[Arrows/1-9]{Style.RESET} Pick Cell  "
            f"{Style.FG_YELLOW}[Space/Enter]{Style.RESET} Mark  "
            f"{Style.FG_YELLOW}[M]{Style.RESET} Mode  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Reset  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ TIC-TAC-TOE (XO) CHAMPIONSHIP ★", body, box_w, Style.FG_CYAN)

    def run(self):
        self.reset()
        while True:
            key = self.term.get_key()
            if key is not None:
                if not self.handle_input(key):
                    return
            self.term.render_frame(self.render())
            time.sleep(0.025)


# ============================================================================
# GAME 3: 2048 TUI
# ============================================================================

class Game2048:
    TILE_COLORS = {
        0: Style.FG_GRAY,
        2: Style.FG_WHITE,
        4: Style.FG_CYAN,
        8: Style.FG_GREEN,
        16: Style.FG_LIME,
        32: Style.FG_YELLOW,
        64: Style.FG_ORANGE,
        128: Style.FG_PINK,
        256: Style.FG_MAGENTA,
        512: Style.FG_PURPLE,
        1024: Style.FG_RED,
        2048: Style.FG_GOLD,
    }

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.reset()

    def reset(self):
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.prev_state = None
        self.game_over = False
        self.won_2048 = False
        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 4 if random.random() < 0.1 else 2

    def compress_and_merge(self, line: list[int]) -> tuple[list[int], int]:
        non_zero = [v for v in line if v != 0]
        merged = []
        gained = 0
        i = 0
        while i < len(non_zero):
            if i + 1 < len(non_zero) and non_zero[i] == non_zero[i + 1]:
                val = non_zero[i] * 2
                merged.append(val)
                gained += val
                i += 2
            else:
                merged.append(non_zero[i])
                i += 1
        while len(merged) < 4:
            merged.append(0)
        return merged, gained

    def move(self, direction: str):
        if self.game_over:
            return
        old_grid = [row[:] for row in self.grid]
        old_score = self.score
        total_gained = 0

        if direction == "LEFT":
            for r in range(4):
                self.grid[r], g = self.compress_and_merge(self.grid[r])
                total_gained += g
        elif direction == "RIGHT":
            for r in range(4):
                rev, g = self.compress_and_merge(self.grid[r][::-1])
                self.grid[r] = rev[::-1]
                total_gained += g
        elif direction == "UP":
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)]
                new_col, g = self.compress_and_merge(col)
                for r in range(4):
                    self.grid[r][c] = new_col[r]
                total_gained += g
        elif direction == "DOWN":
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)][::-1]
                new_col, g = self.compress_and_merge(col)
                new_col = new_col[::-1]
                for r in range(4):
                    self.grid[r][c] = new_col[r]
                total_gained += g

        if self.grid != old_grid:
            self.prev_state = (old_grid, old_score)
            self.score += total_gained
            if self.score > self.scores["game_2048_high"]:
                self.scores["game_2048_high"] = self.score
                save_scores(self.scores)
            for row in self.grid:
                if 2048 in row:
                    self.won_2048 = True
            self.spawn_tile()
            if not self.can_move():
                self.game_over = True

    def can_move(self) -> bool:
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    return True
                if c < 3 and self.grid[r][c] == self.grid[r][c + 1]:
                    return True
                if r < 3 and self.grid[r][c] == self.grid[r + 1][c]:
                    return True
        return False

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key == "U" and self.prev_state:
            self.grid, self.score = self.prev_state
            self.prev_state = None
            self.game_over = False
            return True
        if key in ("UP", "DOWN", "LEFT", "RIGHT"):
            self.move(key)
        return True

    def render(self) -> list[str]:
        box_w = 58
        body = [
            pad_center(
                f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<7}{Style.RESET}   "
                f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores['game_2048_high']}{Style.RESET}",
                box_w - 2,
            ),
            "",
            pad_center(f"{Style.FG_GRAY}┌────────┬────────┬────────┬────────┐{Style.RESET}", box_w - 2),
        ]

        for r in range(4):
            for sub in range(3):
                row_parts = [f"{Style.FG_GRAY}│{Style.RESET}"]
                for c in range(4):
                    val = self.grid[r][c]
                    col = self.TILE_COLORS.get(val, Style.FG_GOLD)
                    if sub == 1:
                        label = f"{val:^8}" if val > 0 else "   ·    "
                        row_parts.append(f"{col}{Style.BOLD}{label}{Style.RESET}")
                    else:
                        row_parts.append("        ")
                    row_parts.append(f"{Style.FG_GRAY}│{Style.RESET}")
                body.append(pad_center("".join(row_parts), box_w - 2))
            if r < 3:
                body.append(pad_center(f"{Style.FG_GRAY}├────────┼────────┼────────┼────────┤{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{Style.FG_GRAY}└────────┴────────┴────────┴────────┘{Style.RESET}", box_w - 2))
        body.append("")

        if self.game_over:
            msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}  NO MORE MOVES! Press [U] Undo or [R] Restart  {Style.RESET}"
        elif self.won_2048:
            msg = f"{Style.BG_WIN}{Style.FG_GOLD}{Style.BOLD}  ★ 2048 REACHED! Keep playing for High Score! ★  {Style.RESET}"
        else:
            msg = f"{Style.DIM}Slide tiles with Arrow Keys or WASD to reach 2048{Style.RESET}"
        body.append(pad_center(msg, box_w - 2))
        body.append("")
        controls = (
            f"{Style.FG_YELLOW}[WASD/Arrows]{Style.RESET} Slide  "
            f"{Style.FG_YELLOW}[U]{Style.RESET} Undo  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Restart  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ 2048 PUZZLE EDITION ★", body, box_w, Style.FG_GOLD)

    def run(self):
        self.reset()
        while True:
            key = self.term.get_key()
            if key is not None:
                if not self.handle_input(key):
                    return
            self.term.render_frame(self.render())
            time.sleep(0.025)


# ============================================================================
# GAME 4: CONNECT FOUR (4-IN-A-ROW) TUI
# ============================================================================

class ConnectFourGame:
    ROWS = 6
    COLS = 7

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.vs_ai = True
        self.cursor_col = 3
        self.reset()

    def reset(self):
        self.grid = [[0] * self.COLS for _ in range(self.ROWS)]
        self.turn = 1  # 1 = Red/Yellow P1, 2 = Cyan/AI P2
        self.winner = None  # 1, 2, or "DRAW"
        self.win_cells = set()

    def get_drop_row(self, board, col: int) -> int | None:
        for r in range(self.ROWS - 1, -1, -1):
            if board[r][col] == 0:
                return r
        return None

    def check_win(self, board):
        # Horizontal, vertical, and both diagonals
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(self.ROWS):
            for c in range(self.COLS):
                p = board[r][c]
                if p == 0:
                    continue
                for dr, dc in directions:
                    cells = [(r + i * dr, c + i * dc) for i in range(4)]
                    if all(
                        0 <= nr < self.ROWS and 0 <= nc < self.COLS and board[nr][nc] == p
                        for nr, nc in cells
                    ):
                        return p, set(cells)
        if all(board[0][c] != 0 for c in range(self.COLS)):
            return "DRAW", set()
        return None, set()

    def ai_choose_col(self) -> int:
        valid_cols = [c for c in range(self.COLS) if self.get_drop_row(self.grid, c) is not None]
        # 1. Check immediate AI win
        for c in valid_cols:
            r = self.get_drop_row(self.grid, c)
            self.grid[r][c] = 2
            w, _ = self.check_win(self.grid)
            self.grid[r][c] = 0
            if w == 2:
                return c
        # 2. Block immediate P1 win
        for c in valid_cols:
            r = self.get_drop_row(self.grid, c)
            self.grid[r][c] = 1
            w, _ = self.check_win(self.grid)
            self.grid[r][c] = 0
            if w == 1:
                return c
        # 3. Prefer center columns and avoid giving P1 a winning spot above
        safe_cols = []
        for c in valid_cols:
            r = self.get_drop_row(self.grid, c)
            self.grid[r][c] = 2
            gives_win = False
            if r > 0:
                self.grid[r - 1][c] = 1
                w, _ = self.check_win(self.grid)
                self.grid[r - 1][c] = 0
                if w == 1:
                    gives_win = True
            self.grid[r][c] = 0
            if not gives_win:
                safe_cols.append(c)

        pool = safe_cols if safe_cols else valid_cols
        pool.sort(key=lambda c: abs(c - 3) + random.uniform(0, 0.4))
        return pool[0]

    def drop_disc(self, col: int):
        if self.winner:
            return
        r = self.get_drop_row(self.grid, col)
        if r is None:
            return
        self.grid[r][col] = self.turn
        self._post_turn()

        if not self.winner and self.vs_ai and self.turn == 2:
            ai_col = self.ai_choose_col()
            ar = self.get_drop_row(self.grid, ai_col)
            if ar is not None:
                self.grid[ar][ai_col] = 2
                self._post_turn()

    def _post_turn(self):
        w, cells = self.check_win(self.grid)
        if w:
            self.winner = w
            self.win_cells = cells
            if w == 1:
                self.scores["c4_p1_wins"] += 1
            elif w == 2:
                self.scores["c4_p2_wins"] += 1
            save_scores(self.scores)
        else:
            self.turn = 2 if self.turn == 1 else 1

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key in ("M", "TAB"):
            self.vs_ai = not self.vs_ai
            self.reset()
            return True
        if key in "1234567" and len(key) == 1:
            col = int(key) - 1
            self.cursor_col = col
            self.drop_disc(col)
            return True
        if key == "LEFT":
            self.cursor_col = (self.cursor_col - 1) % self.COLS
        elif key == "RIGHT":
            self.cursor_col = (self.cursor_col + 1) % self.COLS
        elif key in ("DOWN", "ENTER", "SPACE"):
            if self.winner:
                self.reset()
            else:
                self.drop_disc(self.cursor_col)
        return True

    def render(self) -> list[str]:
        box_w = 76
        mode_str = "1P vs Tactical AI" if self.vs_ai else "2P Local (Pass & Play)"
        p2_name = "AI (Gold)" if self.vs_ai else "P2 (Gold)"

        body = [
            pad_center(f"{Style.BOLD}MODE:{Style.RESET} {Style.FG_CYAN}{mode_str}{Style.RESET}", box_w - 2),
            pad_center(
                f"{Style.FG_RED}● P1 Wins: {self.scores['c4_p1_wins']}{Style.RESET}     "
                f"{Style.FG_GOLD}● {p2_name} Wins: {self.scores['c4_p2_wins']}{Style.RESET}",
                box_w - 2,
            ),
            "",
        ]

        # Column dropper indicator
        drop_col = Style.FG_RED if self.turn == 1 else Style.FG_GOLD
        indicator = []
        for c in range(self.COLS):
            if c == self.cursor_col and not self.winner:
                indicator.append(f" {drop_col}{Style.BOLD}▼▼{Style.RESET} ")
            else:
                indicator.append(f" {Style.FG_GRAY}{c + 1} {Style.RESET} ")
        body.append(pad_center(" ".join(indicator), box_w - 2))

        body.append(pad_center(f"{Style.FG_BLUE}╔════╤════╤════╤════╤════╤════╤════╗{Style.RESET}", box_w - 2))
        for r in range(self.ROWS):
            row_cells = [f"{Style.FG_BLUE}║{Style.RESET}"]
            for c in range(self.COLS):
                val = self.grid[r][c]
                is_win = (r, c) in self.win_cells
                bg = Style.BG_WIN if is_win else ""
                if val == 1:
                    disc = f"{bg}{Style.FG_RED}{Style.BOLD} ●● {Style.RESET}"
                elif val == 2:
                    disc = f"{bg}{Style.FG_GOLD}{Style.BOLD} ●● {Style.RESET}"
                else:
                    disc = f"{Style.FG_GRAY} ·· {Style.RESET}"
                row_cells.append(disc)
                sep = "║" if c == self.COLS - 1 else "│"
                row_cells.append(f"{Style.FG_BLUE}{sep}{Style.RESET}")
            body.append(pad_center("".join(row_cells), box_w - 2))
        body.append(pad_center(f"{Style.FG_BLUE}╚════╧════╧════╧════╧════╧════╧════╝{Style.RESET}", box_w - 2))
        body.append("")

        if self.winner:
            if self.winner == "DRAW":
                status = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}  === FULL BOARD DRAW! Press [ENTER/R] to Replay ===  {Style.RESET}"
            else:
                who = "PLAYER 1 (RED)" if self.winner == 1 else ("AI (GOLD)" if self.vs_ai else "PLAYER 2 (GOLD)")
                status = f"{Style.BG_WIN}{Style.FG_GOLD}{Style.BOLD}  ★ {who} CONNECTS 4! Press [ENTER/R] ★  {Style.RESET}"
        else:
            t_col = Style.FG_RED if self.turn == 1 else Style.FG_GOLD
            t_who = "Player 1 (Red)" if self.turn == 1 else p2_name
            status = f"Turn: {t_col}{Style.BOLD}{t_who}{Style.RESET} — [Left/Right] or [1-7] + [Space/Enter]"

        body.append(pad_center(status, box_w - 2))
        body.append("")
        controls = (
            f"{Style.FG_YELLOW}[◄/► or 1-7]{Style.RESET} Column  "
            f"{Style.FG_YELLOW}[Space/Enter]{Style.RESET} Drop  "
            f"{Style.FG_YELLOW}[M]{Style.RESET} Mode  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Reset  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ CONNECT FOUR ARCADE ★", body, box_w, Style.FG_BLUE)

    def run(self):
        self.reset()
        while True:
            key = self.term.get_key()
            if key is not None:
                if not self.handle_input(key):
                    return
            self.term.render_frame(self.render())
            time.sleep(0.025)


# ============================================================================
# GAME 5: PING PONG (TABLE TENNIS) TUI
# ============================================================================

class PongGame:
    MODES = [
        ("1P vs AI (Casual)", 0.48),
        ("1P vs AI (Pro)", 0.72),
        ("1P vs AI (Impossible)", 0.96),
        ("2P Local (W/S vs Up/Down)", 0.0),
    ]
    WIN_SCORE = 7

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.w = 58
        self.h = 15
        self.paddle_h = 3
        self.mode_idx = 1  # Pro AI
        self.reset_match()

    def reset_match(self):
        self.p1_score = 0
        self.p2_score = 0
        self.rally = 0
        self.max_rally = 0
        self.paused = False
        self.winner = None
        self.reset_ball(direction=random.choice([-1, 1]))

    def reset_ball(self, direction: int = 1):
        self.p1_y = float(self.h // 2 - self.paddle_h // 2)
        self.p2_y = float(self.h // 2 - self.paddle_h // 2)
        self.bx = float(self.w // 2)
        self.by = float(self.h // 2)
        self.vx = 0.85 * direction
        self.vy = random.choice([-0.38, -0.25, 0.25, 0.38])
        self.rally = 0
        self.serve_pause = 12  # brief pause before ball launches

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset_match()
            return True
        if key == "P" or (key == "SPACE" and not self.winner):
            self.paused = not self.paused
            return True
        if key in ("ENTER", "SPACE") and self.winner:
            self.reset_match()
            return True
        if key in ("M", "TAB"):
            self.mode_idx = (self.mode_idx + 1) % len(self.MODES)
            self.reset_match()
            return True

        # Fallback discrete movement if hardware key-hold isn't active
        if not self.paused and not self.winner:
            if not (self.term.is_key_down("UP") or self.term.is_key_down("DOWN") or self.term.is_key_down("W") or self.term.is_key_down("S")):
                if key == "UP":
                    self.p1_y = max(0.0, self.p1_y - 1.2)
                elif key == "DOWN":
                    self.p1_y = min(float(self.h - self.paddle_h), self.p1_y + 1.2)
        return True

    def step(self):
        if self.paused or self.winner:
            return

        is_2p = (self.mode_idx == 3)
        paddle_speed = 0.72

        # Smooth hardware-polled paddle movement
        if is_2p:
            if self.term.is_key_down("W"):
                self.p1_y = max(0.0, self.p1_y - paddle_speed)
            if self.term.is_key_down("S"):
                self.p1_y = min(float(self.h - self.paddle_h), self.p1_y + paddle_speed)
            if self.term.is_key_down("UP"):
                self.p2_y = max(0.0, self.p2_y - paddle_speed)
            if self.term.is_key_down("DOWN"):
                self.p2_y = min(float(self.h - self.paddle_h), self.p2_y + paddle_speed)
        else:
            if self.term.is_key_down("W") or self.term.is_key_down("UP"):
                self.p1_y = max(0.0, self.p1_y - paddle_speed)
            if self.term.is_key_down("S") or self.term.is_key_down("DOWN"):
                self.p1_y = min(float(self.h - self.paddle_h), self.p1_y + paddle_speed)

            # AI Paddle tracking
            _, ai_speed = self.MODES[self.mode_idx]
            target_y = (self.by - self.paddle_h / 2.0) if self.vx > 0 else (self.h / 2.0 - self.paddle_h / 2.0)
            diff = target_y - self.p2_y
            if abs(diff) > 0.35:
                move = min(ai_speed, abs(diff)) * (1 if diff > 0 else -1)
                self.p2_y = max(0.0, min(float(self.h - self.paddle_h), self.p2_y + move))

        if self.serve_pause > 0:
            self.serve_pause -= 1
            return

        # Advance ball
        self.bx += self.vx
        self.by += self.vy

        # Top/Bottom wall bounce
        if self.by <= 0.0:
            self.by = 0.0
            self.vy = abs(self.vy)
        elif self.by >= self.h - 1.0:
            self.by = float(self.h - 1)
            self.vy = -abs(self.vy)

        # Left Paddle (x = 2) collision
        p1_top = int(round(self.p1_y))
        if self.vx < 0 and 1.5 <= self.bx <= 3.1:
            by_i = int(round(self.by))
            if p1_top - 1 <= by_i <= p1_top + self.paddle_h:
                self.bx = 3.1
                offset = (self.by - (self.p1_y + self.paddle_h / 2.0)) / (self.paddle_h / 2.0)
                speed = min(1.55, abs(self.vx) * 1.06 + 0.02)
                self.vx = speed
                self.vy = max(-0.85, min(0.85, offset * 0.58 + random.uniform(-0.05, 0.05)))
                self._on_rally_hit()

        # Right Paddle (x = w - 3) collision
        p2_top = int(round(self.p2_y))
        if self.vx > 0 and (self.w - 4.1) <= self.bx <= (self.w - 2.5):
            by_i = int(round(self.by))
            if p2_top - 1 <= by_i <= p2_top + self.paddle_h:
                self.bx = float(self.w - 4.1)
                offset = (self.by - (self.p2_y + self.paddle_h / 2.0)) / (self.paddle_h / 2.0)
                speed = min(1.55, abs(self.vx) * 1.06 + 0.02)
                self.vx = -speed
                self.vy = max(-0.85, min(0.85, offset * 0.58 + random.uniform(-0.05, 0.05)))
                self._on_rally_hit()

        # Scoring
        if self.bx < 0:
            self.p2_score += 1
            if self.p2_score >= self.WIN_SCORE:
                self.winner = 2
                self.scores["pong_p2_wins"] = self.scores.get("pong_p2_wins", 0) + 1
                save_scores(self.scores)
            else:
                self.reset_ball(direction=1)
        elif self.bx >= self.w:
            self.p1_score += 1
            if self.p1_score >= self.WIN_SCORE:
                self.winner = 1
                self.scores["pong_p1_wins"] = self.scores.get("pong_p1_wins", 0) + 1
                save_scores(self.scores)
            else:
                self.reset_ball(direction=-1)

    def _on_rally_hit(self):
        self.rally += 1
        if self.rally > self.scores.get("pong_best_rally", 0):
            self.scores["pong_best_rally"] = self.rally
            save_scores(self.scores)

    def render(self) -> list[str]:
        box_w = 78
        mode_name, _ = self.MODES[self.mode_idx]
        p2_tag = "P2" if self.mode_idx == 3 else "AI"

        header = (
            f"{Style.FG_CYAN}{Style.BOLD}P1: {self.p1_score:02d}{Style.RESET}   "
            f"{Style.FG_GRAY}vs (First to {self.WIN_SCORE}){Style.RESET}   "
            f"{Style.FG_PINK}{Style.BOLD}{p2_tag}: {self.p2_score:02d}{Style.RESET}     "
            f"{Style.BOLD}RALLY:{Style.RESET} {Style.FG_GOLD}{self.rally:<3}{Style.RESET} "
            f"{Style.DIM}(Best: {self.scores.get('pong_best_rally', 0)}){Style.RESET}"
        )
        sub_header = f"{Style.BOLD}MODE:{Style.RESET} {Style.FG_YELLOW}{mode_name}{Style.RESET}"

        body = [
            pad_center(header, box_w - 2),
            pad_center(sub_header, box_w - 2),
            pad_center(f"{Style.FG_CYAN}┌{'─' * (self.w // 2)}┬{'─' * (self.w - self.w // 2 - 1)}┐{Style.RESET}", box_w - 2),
        ]

        p1_top = int(round(self.p1_y))
        p2_top = int(round(self.p2_y))
        bx_i = int(round(self.bx))
        by_i = int(round(self.by))
        is_smash = abs(self.vx) >= 1.2

        for r in range(self.h):
            row_chars = []
            for c in range(self.w):
                if c == 2 and p1_top <= r < p1_top + self.paddle_h:
                    row_chars.append(f"{Style.FG_CYAN}{Style.BOLD}█{Style.RESET}")
                elif c == self.w - 3 and p2_top <= r < p2_top + self.paddle_h:
                    row_chars.append(f"{Style.FG_PINK}{Style.BOLD}█{Style.RESET}")
                elif c == bx_i and r == by_i:
                    b_col = Style.FG_RED if is_smash else Style.FG_GOLD
                    row_chars.append(f"{b_col}{Style.BOLD}●{Style.RESET}")
                elif c == self.w // 2:
                    row_chars.append(f"{Style.FG_GRAY}┊{Style.RESET}")
                else:
                    row_chars.append(" ")

            row_str = "".join(row_chars)
            if self.winner and r in (self.h // 2 - 1, self.h // 2):
                if r == self.h // 2 - 1:
                    who = "PLAYER 1 WINS THE MATCH!" if self.winner == 1 else f"{p2_tag} WINS THE MATCH!"
                    msg = f"{Style.BG_WIN}{Style.FG_GOLD}{Style.BOLD}  ★ {who} ({self.p1_score} - {self.p2_score}) ★  {Style.RESET}"
                else:
                    msg = f"{Style.BG_WIN}{Style.FG_WHITE}   Press [ENTER/R] to Play Again or [Q] Menu   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            elif self.paused and r == self.h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P/SPACE] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, self.w)

            body.append(pad_center(f"{Style.FG_CYAN}│{Style.RESET}{row_str}{Style.FG_CYAN}│{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{Style.FG_CYAN}└{'─' * (self.w // 2)}┴{'─' * (self.w - self.w // 2 - 1)}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[W/S or ▲/▼]{Style.RESET} Paddle  "
            f"{Style.FG_YELLOW}[P]{Style.RESET} Pause  "
            f"{Style.FG_YELLOW}[M]{Style.RESET} Mode/AI  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Restart  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ PING PONG ARCADE CHAMPIONSHIP ★", body, box_w, Style.FG_CYAN)

    def run(self):
        self.reset_match()
        last_step = time.perf_counter()
        while True:
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            now = time.perf_counter()
            if now - last_step >= 0.032:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.012)


# ============================================================================
# GAME 6: STARFIGHTER (SHOOT 'EM UP / SHMUP) TUI
# ============================================================================

class SpaceShooterGame:
    """Vertical-scrolling Galaga / Space-Invaders style Shoot 'Em Up with SHIFT Phase-Dodge."""

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.w = 52
        self.h = 16
        self.auto_fire = True
        self.reset()

    def reset(self):
        self.px = self.w // 2
        self.py = self.h - 2
        self.last_dir = (1, 0)
        self.lives = 3
        self.shield = False
        self.weapon_lv = 1
        self.bombs = 2
        self.score = 0
        self.wave = 1
        self.ticks = 0
        self.fire_cooldown = 0
        self.invuln_ticks = 0
        self.dodge_cd = 0
        self.dodge_active = 0
        self.graze_ticks = 0
        self.shift_was_down = False
        self.bomb_flash = 0
        self.paused = False
        self.game_over = False

        self.bullets = []        # [x, y, vx, vy]
        self.enemy_bullets = []  # [x, y, vx, vy]
        self.enemies = []        # dict: x, y, vx, hp, max_hp, kind, timer
        self.powerups = []       # [x, y, kind]  kind in ('W', 'S', 'B', '+')
        self.particles = []      # [x, y, ttl, ch, col]
        self.stars = [
            [random.randint(0, self.w - 1), random.randint(0, self.h - 1), random.choice([1, 2])]
            for _ in range(22)
        ]
        self.spawn_wave()

    def trigger_dodge(self):
        """Perform an evasive Barrel-Roll / Phase-Dodge on SHIFT press."""
        if self.dodge_cd > 0 or self.paused or self.game_over:
            return
        self.dodge_cd = 16
        self.dodge_active = 7
        self.invuln_ticks = max(self.invuln_ticks, 9)

        dx, dy = self.last_dir
        if dx == 0 and dy == 0:
            dx = 1

        steps = 6 if dx != 0 else 3
        grazed = 0
        for s in range(1, steps + 1):
            # Leave afterimage ghost trail
            col = Style.FG_MAGENTA if s % 2 == 0 else Style.FG_CYAN
            self.particles.append([float(self.px), float(self.py), 4, "«", col])
            self.particles.append([float(self.px + 1), float(self.py), 4, "»", col])
            self.px = max(2, min(self.w - 3, self.px + dx))
            self.py = max(self.h // 2, min(self.h - 1, self.py + dy))

            # Check bullet graze along the dash path
            surviving_eb = []
            for eb in self.enemy_bullets:
                if abs(eb[0] - self.px) <= 2.2 and abs(eb[1] - self.py) <= 1.5:
                    grazed += 1
                    self.particles.append([eb[0], eb[1], 3, "*", Style.FG_GOLD])
                else:
                    surviving_eb.append(eb)
            self.enemy_bullets = surviving_eb

        if grazed > 0:
            self.score += grazed * 25
            self.graze_ticks = 16
            if self.score > self.scores.get("shmup_high", 0):
                self.scores["shmup_high"] = self.score
                save_scores(self.scores)

    def spawn_wave(self):
        self.enemies.clear()
        if self.wave % 3 == 0:
            # BOSS DREADNOUGHT WAVE!
            boss_hp = 25 + self.wave * 10
            self.enemies.append({
                "x": float(self.w // 2),
                "y": 2.0,
                "vx": 0.45,
                "hp": boss_hp,
                "max_hp": boss_hp,
                "kind": "BOSS",
                "timer": 0,
            })
            # Plus two escort fighters
            for ex in (10, self.w - 11):
                self.enemies.append({
                    "x": float(ex),
                    "y": 3.0,
                    "vx": 0.3,
                    "hp": 3,
                    "max_hp": 3,
                    "kind": "FIGHTER",
                    "timer": random.randint(0, 20),
                })
        else:
            # Standard formation wave of Scouts, Fighters, and Cruisers
            num_scouts = min(8, 4 + self.wave)
            spacing = max(5, (self.w - 8) // max(1, num_scouts))
            for i in range(num_scouts):
                ex = 4 + i * spacing
                self.enemies.append({
                    "x": float(min(self.w - 4, ex)),
                    "y": 1.0 + (i % 2),
                    "vx": 0.25 if i % 2 == 0 else -0.25,
                    "hp": 1 + (self.wave // 4),
                    "max_hp": 1 + (self.wave // 4),
                    "kind": "SCOUT",
                    "timer": i * 7,
                })

            num_fighters = min(5, 1 + self.wave // 2)
            for i in range(num_fighters):
                ex = 8 + i * ((self.w - 16) // max(1, num_fighters))
                self.enemies.append({
                    "x": float(min(self.w - 5, ex)),
                    "y": 3.0,
                    "vx": 0.35,
                    "hp": 2 + (self.wave // 3),
                    "max_hp": 2 + (self.wave // 3),
                    "kind": "FIGHTER",
                    "timer": i * 11,
                })

            if self.wave >= 2:
                self.enemies.append({
                    "x": float(self.w // 2),
                    "y": 1.0,
                    "vx": 0.2,
                    "hp": 5 + self.wave,
                    "max_hp": 5 + self.wave,
                    "kind": "CRUISER",
                    "timer": 5,
                })

    def fire_player_weapon(self):
        if self.fire_cooldown > 0:
            return
        if self.weapon_lv == 1:
            self.bullets.append([float(self.px), float(self.py - 1), 0.0, -1.0])
            self.fire_cooldown = 3
        elif self.weapon_lv == 2:
            self.bullets.append([float(self.px - 1), float(self.py - 1), 0.0, -1.0])
            self.bullets.append([float(self.px + 1), float(self.py - 1), 0.0, -1.0])
            self.fire_cooldown = 3
        else:
            self.bullets.append([float(self.px), float(self.py - 1), 0.0, -1.0])
            self.bullets.append([float(self.px - 1), float(self.py - 1), -0.25, -0.95])
            self.bullets.append([float(self.px + 1), float(self.py - 1), 0.25, -0.95])
            self.fire_cooldown = 3

    def trigger_bomb(self):
        if self.bombs <= 0 or self.paused or self.game_over:
            return
        self.bombs -= 1
        self.bomb_flash = 4
        self.enemy_bullets.clear()
        survivors = []
        for e in self.enemies:
            e["hp"] -= 15
            if e["hp"] <= 0:
                self._on_enemy_destroyed(e)
            else:
                survivors.append(e)
        self.enemies = survivors

    def _on_enemy_destroyed(self, e: dict):
        pts = {"SCOUT": 20, "FIGHTER": 45, "CRUISER": 100, "BOSS": 500}.get(e["kind"], 25)
        self.score += pts
        if self.score > self.scores.get("shmup_high", 0):
            self.scores["shmup_high"] = self.score
            save_scores(self.scores)

        # Spawn explosion particles
        for _ in range(7 if e["kind"] != "BOSS" else 18):
            ox = e["x"] + random.randint(-2, 2)
            oy = e["y"] + random.randint(-1, 1)
            self.particles.append([
                ox, oy, random.randint(3, 6),
                random.choice(["*", "+", "#"]),
                random.choice([Style.FG_GOLD, Style.FG_RED, Style.FG_ORANGE]),
            ])

        # Chance to drop a power-up capsule
        drop_chance = 1.0 if e["kind"] in ("CRUISER", "BOSS") else 0.18
        if random.random() < drop_chance:
            kind = random.choice(["W", "W", "S", "B", "+"])
            self.powerups.append([e["x"], e["y"], kind])

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key == "P":
            self.paused = not self.paused
            return True
        if key in ("F", "M", "TAB"):
            self.auto_fire = not self.auto_fire
            return True
        if key in ("B", "X"):
            self.trigger_bomb()
            return True
        if key in ("SHIFT", "C"):
            self.trigger_dodge()
            return True
        if key in ("ENTER", "SPACE") and self.game_over:
            self.reset()
            return True

        if not self.paused and not self.game_over:
            if key in ("SPACE", "Z"):
                self.fire_player_weapon()
            # Discrete fallback movement if hardware key polling isn't active
            if not (
                self.term.is_key_down("LEFT") or self.term.is_key_down("RIGHT")
                or self.term.is_key_down("A") or self.term.is_key_down("D")
                or self.term.is_key_down("UP") or self.term.is_key_down("DOWN")
                or self.term.is_key_down("W") or self.term.is_key_down("S")
            ):
                if key == "LEFT":
                    self.last_dir = (-1, 0)
                    self.px = max(2, self.px - 2)
                elif key == "RIGHT":
                    self.last_dir = (1, 0)
                    self.px = min(self.w - 3, self.px + 2)
                elif key == "UP":
                    self.last_dir = (0, -1)
                    self.py = max(self.h // 2, self.py - 1)
                elif key == "DOWN":
                    self.last_dir = (0, 1)
                    self.py = min(self.h - 1, self.py + 1)
        return True

    def step(self):
        if self.paused or self.game_over:
            return

        self.ticks += 1
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.dodge_cd > 0:
            self.dodge_cd -= 1
        if self.dodge_active > 0:
            self.dodge_active -= 1
        if self.graze_ticks > 0:
            self.graze_ticks -= 1
        if self.bomb_flash > 0:
            self.bomb_flash -= 1

        # Smooth hardware-polled starfighter movement
        mx, my = 0, 0
        if self.term.is_key_down("LEFT") or self.term.is_key_down("A"):
            mx -= 1
        if self.term.is_key_down("RIGHT") or self.term.is_key_down("D"):
            mx += 1
        if self.term.is_key_down("UP") or self.term.is_key_down("W"):
            my -= 1
        if self.term.is_key_down("DOWN") or self.term.is_key_down("S"):
            my += 1

        if mx != 0 or my != 0:
            self.last_dir = (mx, my)
            self.px = max(2, min(self.w - 3, self.px + mx))
            self.py = max(self.h // 2, min(self.h - 1, self.py + my))

        # Check SHIFT Dodge button
        shift_now = self.term.is_key_down("SHIFT") or self.term.is_key_down("C")
        if shift_now and not self.shift_was_down:
            self.trigger_dodge()
        self.shift_was_down = shift_now

        if self.auto_fire or self.term.is_key_down("SPACE") or self.term.is_key_down("Z"):
            self.fire_player_weapon()

        # Scroll starfield
        for s in self.stars:
            if self.ticks % s[2] == 0:
                s[1] = (s[1] + 1) % self.h

        # Update player bullets
        new_bullets = []
        for b in self.bullets:
            b[0] += b[2]
            b[1] += b[3]
            if 0 <= b[0] < self.w and 0 <= b[1] < self.h:
                new_bullets.append(b)
        self.bullets = new_bullets

        # Update enemies & check player bullet hits
        for e in self.enemies:
            e["timer"] += 1
            e["x"] += e["vx"]
            margin = 5 if e["kind"] == "BOSS" else 3
            if e["x"] <= margin or e["x"] >= self.w - 1 - margin:
                e["vx"] = -e["vx"]
                if e["kind"] != "BOSS" and e["y"] < self.h - 5:
                    e["y"] = min(float(self.h - 5), e["y"] + 0.4)

            # Enemy firing patterns
            if e["kind"] == "FIGHTER" and e["timer"] % max(16, 34 - self.wave * 2) == 0:
                self.enemy_bullets.append([e["x"], e["y"] + 1.0, 0.0, 0.45])
            elif e["kind"] == "CRUISER" and e["timer"] % max(14, 28 - self.wave) == 0:
                self.enemy_bullets.append([e["x"] - 1, e["y"] + 1.0, -0.12, 0.45])
                self.enemy_bullets.append([e["x"] + 1, e["y"] + 1.0, 0.12, 0.45])
            elif e["kind"] == "BOSS" and e["timer"] % 10 == 0:
                for vx in (-0.28, 0.0, 0.28):
                    self.enemy_bullets.append([e["x"] + vx * 6, e["y"] + 1.0, vx, 0.48])

        # Bullet-Enemy collision
        surviving_enemies = []
        for e in self.enemies:
            hit_radius = 4.2 if e["kind"] == "BOSS" else (2.4 if e["kind"] == "CRUISER" else 1.8)
            remaining_bullets = []
            for b in self.bullets:
                if abs(b[0] - e["x"]) <= hit_radius and abs(b[1] - e["y"]) <= 1.1:
                    e["hp"] -= 1
                    self.particles.append([b[0], b[1], 2, "+", Style.FG_YELLOW])
                else:
                    remaining_bullets.append(b)
            self.bullets = remaining_bullets

            if e["hp"] <= 0:
                self._on_enemy_destroyed(e)
            else:
                surviving_enemies.append(e)
        self.enemies = surviving_enemies

        # Update enemy bullets & check player collision
        new_eb = []
        for eb in self.enemy_bullets:
            eb[0] += eb[2]
            eb[1] += eb[3]
            if 0 <= eb[0] < self.w and 0 <= eb[1] < self.h:
                if abs(eb[0] - self.px) <= 1.3 and abs(eb[1] - self.py) <= 0.8:
                    self._damage_player()
                else:
                    new_eb.append(eb)
        self.enemy_bullets = new_eb

        # Update power-up capsules
        new_pu = []
        for pu in self.powerups:
            pu[1] += 0.25
            if abs(pu[0] - self.px) <= 2.0 and abs(pu[1] - self.py) <= 1.2:
                kind = pu[2]
                if kind == "W":
                    if self.weapon_lv < 3:
                        self.weapon_lv += 1
                    else:
                        self.score += 100
                elif kind == "S":
                    self.shield = True
                elif kind == "B":
                    self.bombs = min(5, self.bombs + 1)
                elif kind == "+":
                    self.lives = min(5, self.lives + 1)
            elif pu[1] < self.h:
                new_pu.append(pu)
        self.powerups = new_pu

        # Update explosion particles
        self.particles = [[p[0], p[1], p[2] - 1, p[3], p[4]] for p in self.particles if p[2] > 1]

        # Check wave clear
        if not self.enemies:
            self.wave += 1
            if self.wave > self.scores.get("shmup_max_wave", 1):
                self.scores["shmup_max_wave"] = self.wave
                save_scores(self.scores)
            self.spawn_wave()

    def _damage_player(self):
        if self.invuln_ticks > 0 or self.dodge_active > 0:
            return
        if self.shield:
            self.shield = False
            self.invuln_ticks = 18
            return
        self.lives -= 1
        self.weapon_lv = max(1, self.weapon_lv - 1)
        self.invuln_ticks = 24
        for _ in range(8):
            self.particles.append([
                self.px + random.randint(-2, 2),
                self.py + random.randint(-1, 1),
                4, "*", Style.FG_RED,
            ])
        if self.lives <= 0:
            self.game_over = True

    def render(self) -> list[str]:
        box_w = 84
        hearts = f"{Style.FG_RED}{'♥' * self.lives}{Style.FG_GRAY}{'·' * max(0, 5 - self.lives)}{Style.RESET}"
        bombs_str = f"{Style.FG_ORANGE}{'★' * self.bombs}{Style.RESET}"
        dodge_str = (
            f"{Style.FG_LIME}READY{Style.RESET}"
            if self.dodge_cd == 0
            else f"{Style.FG_YELLOW}CD:{self.dodge_cd:<2}{Style.RESET}"
        )

        header = (
            f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<6}{Style.RESET} "
            f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores.get('shmup_high', 0):<6}{Style.RESET} "
            f"{Style.BOLD}WAVE:{Style.RESET} {Style.FG_CYAN}{self.wave:<2}{Style.RESET} "
            f"{Style.BOLD}HULL:{Style.RESET} {hearts} "
            f"{Style.BOLD}DODGE:{Style.RESET} {dodge_str} "
            f"{Style.BOLD}WPN:{Style.RESET} {Style.FG_YELLOW}Lv.{self.weapon_lv}{Style.RESET} "
            f"{Style.BOLD}BOMB:{Style.RESET} {bombs_str}"
        )
        body = [pad_center(header, box_w - 2)]

        # Boss health bar or wave status line
        boss = next((e for e in self.enemies if e["kind"] == "BOSS"), None)
        if boss:
            filled = max(0, int((boss["hp"] / boss["max_hp"]) * 28))
            boss_bar = (
                f"{Style.FG_RED}{Style.BOLD}WARNING - BOSS DREADNOUGHT: "
                f"[{'█' * filled}{'·' * (28 - filled)}] {boss['hp']}/{boss['max_hp']}{Style.RESET}"
            )
            body.append(pad_center(boss_bar, box_w - 2))
        elif self.graze_ticks > 0:
            body.append(
                pad_center(
                    f"{Style.FG_GOLD}{Style.BOLD}★ PHASE-DODGE GRAZE BONUS! +25 PTS ★{Style.RESET}",
                    box_w - 2,
                )
            )
        else:
            af = f"{Style.FG_GREEN}AUTO-FIRE: ON{Style.RESET}" if self.auto_fire else f"{Style.FG_YELLOW}AUTO-FIRE: OFF{Style.RESET}"
            body.append(pad_center(f"{af} {Style.DIM}— Press [SHIFT] to Phase-Dodge through Enemy Fire!{Style.RESET}", box_w - 2))

        border_col = Style.FG_GOLD if self.bomb_flash > 0 else (Style.FG_MAGENTA if self.dodge_active > 0 else Style.FG_BLUE)
        body.append(pad_center(f"{border_col}┌{'─' * self.w}┐{Style.RESET}", box_w - 2))

        # Build 2D character canvas
        grid = [[" " for _ in range(self.w)] for _ in range(self.h)]

        # 1. Stars
        for sx, sy, spd in self.stars:
            if 0 <= sx < self.w and 0 <= sy < self.h:
                ch = "·" if spd == 2 else "."
                grid[sy][sx] = f"{Style.FG_GRAY}{ch}{Style.RESET}"

        # 2. Power-ups
        for px, py, kind in self.powerups:
            ix, iy = int(round(px)), int(round(py))
            if 0 <= iy < self.h and 1 <= ix < self.w - 1:
                col = Style.FG_GOLD if kind == "W" else (Style.FG_CYAN if kind == "S" else Style.FG_GREEN)
                grid[iy][ix - 1] = f"{col}{Style.BOLD}[{Style.RESET}"
                grid[iy][ix] = f"{col}{Style.BOLD}{kind}{Style.RESET}"
                grid[iy][ix + 1] = f"{col}{Style.BOLD}]{Style.RESET}"

        # 3. Player bullets
        for bx, by, vx, _ in self.bullets:
            ix, iy = int(round(bx)), int(round(by))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                b_ch = "╲" if vx < -0.1 else ("╱" if vx > 0.1 else "│")
                col = Style.FG_MAGENTA if self.weapon_lv == 3 else Style.FG_CYAN
                grid[iy][ix] = f"{col}{Style.BOLD}{b_ch}{Style.RESET}"

        # 4. Enemy bullets
        for ebx, eby, _, _ in self.enemy_bullets:
            ix, iy = int(round(ebx)), int(round(eby))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{Style.FG_RED}{Style.BOLD}!{Style.RESET}"

        # 5. Enemies
        for e in self.enemies:
            ix, iy = int(round(e["x"])), int(round(e["y"]))
            if not (0 <= iy < self.h):
                continue
            if e["kind"] == "SCOUT":
                sprite, col = "‹●›", Style.FG_GREEN
            elif e["kind"] == "FIGHTER":
                sprite, col = "╦█╦", Style.FG_RED
            elif e["kind"] == "CRUISER":
                sprite, col = "╔███╗", Style.FG_MAGENTA
            else:
                sprite, col = "╠═╦███╦═╣", Style.FG_GOLD
            half = len(sprite) // 2
            for idx, ch in enumerate(sprite):
                cx = ix - half + idx
                if 0 <= cx < self.w:
                    grid[iy][cx] = f"{col}{Style.BOLD}{ch}{Style.RESET}"

        # 6. Particles
        for px, py, _, pch, pcol in self.particles:
            ix, iy = int(round(px)), int(round(py))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{pcol}{Style.BOLD}{pch}{Style.RESET}"

        # 7. Player Starfighter
        if not self.game_over and (self.invuln_ticks % 2 == 0 or self.dodge_active > 0):
            if self.dodge_active > 0:
                ship, scol = "«▲»", Style.FG_MAGENTA
            elif self.shield:
                ship, scol = "{▲}", Style.FG_GOLD
            else:
                ship, scol = "◄▲►", Style.FG_CYAN
            for idx, ch in enumerate(ship):
                cx = self.px - 1 + idx
                if 0 <= cx < self.w and 0 <= self.py < self.h:
                    grid[self.py][cx] = f"{scol}{Style.BOLD}{ch}{Style.RESET}"

        for r in range(self.h):
            row_str = "".join(grid[r])
            if self.game_over and r in (self.h // 2 - 1, self.h // 2):
                if r == self.h // 2 - 1:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}  !! STARFIGHTER DESTROYED — SCORE: {self.score:<6} !!  {Style.RESET}"
                else:
                    msg = f"{Style.BG_ALERT}{Style.FG_GOLD}{Style.BOLD}   Press [ENTER/R] to Launch Again or [Q] Menu   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            elif self.paused and r == self.h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, self.w)

            body.append(pad_center(f"{border_col}│{Style.RESET}{row_str}{border_col}│{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{border_col}└{'─' * self.w}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[WASD/Arrows]{Style.RESET} Fly  "
            f"{Style.FG_YELLOW}[SHIFT]{Style.RESET} Dodge  "
            f"{Style.FG_YELLOW}[Space]{Style.RESET} Fire  "
            f"{Style.FG_YELLOW}[B]{Style.RESET} Bomb  "
            f"{Style.FG_YELLOW}[F]{Style.RESET} AutoFire  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ STARFIGHTER: VERTICAL SHOOT 'EM UP ★", body, box_w, Style.FG_BLUE)

    def run(self):
        self.reset()
        last_step = time.perf_counter()
        while True:
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            now = time.perf_counter()
            if now - last_step >= 0.04:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.012)


# ============================================================================
# GAME 7: BRICK BREAKER (ARKANOID) TUI
# ============================================================================

class BrickBreakerGame:
    ROW_COLORS = [
        Style.FG_RED,
        Style.FG_ORANGE,
        Style.FG_GOLD,
        Style.FG_GREEN,
        Style.FG_CYAN,
    ]

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.w = 52
        self.h = 16
        self.reset()

    def reset(self):
        self.level = 1
        self.lives = 3
        self.score = 0
        self.paused = False
        self.game_over = False
        self.setup_level()

    def setup_level(self):
        self.paddle_w = 9
        self.px = float(self.w // 2 - self.paddle_w // 2)
        self.balls = [[float(self.w // 2), float(self.h - 2), 0.55, -0.55]]
        self.powerups = []  # [x, y, kind]  'W'=Wide, 'M'=MultiBall, '+'=Life
        self.bricks = {}    # (r, c) -> hp
        self.brick_cols = 10
        self.brick_w = 5
        for r in range(5):
            for c in range(self.brick_cols):
                hp = 2 if (r == 0 and self.level >= 2) else 1
                self.bricks[(r, c)] = hp

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key in ("P", "SPACE") and not self.game_over:
            self.paused = not self.paused
            return True
        if key in ("ENTER", "SPACE") and self.game_over:
            self.reset()
            return True
        if not self.paused and not self.game_over:
            if not (self.term.is_key_down("LEFT") or self.term.is_key_down("RIGHT") or self.term.is_key_down("A") or self.term.is_key_down("D")):
                if key == "LEFT":
                    self.px = max(0.0, self.px - 2.5)
                elif key == "RIGHT":
                    self.px = min(float(self.w - self.paddle_w), self.px + 2.5)
        return True

    def step(self):
        if self.paused or self.game_over:
            return

        if self.term.is_key_down("LEFT") or self.term.is_key_down("A"):
            self.px = max(0.0, self.px - 1.35)
        if self.term.is_key_down("RIGHT") or self.term.is_key_down("D"):
            self.px = min(float(self.w - self.paddle_w), self.px + 1.35)

        active_balls = []
        for b in self.balls:
            b[0] += b[2]
            b[1] += b[3]

            # Wall collisions
            if b[0] <= 0.0:
                b[0] = 0.0
                b[2] = abs(b[2])
            elif b[0] >= self.w - 1.0:
                b[0] = float(self.w - 1)
                b[2] = -abs(b[2])
            if b[1] <= 0.0:
                b[1] = 0.0
                b[3] = abs(b[3])

            # Paddle collision
            if b[3] > 0 and (self.h - 2.2) <= b[1] <= (self.h - 1.0):
                if self.px - 0.8 <= b[0] <= self.px + self.paddle_w + 0.8:
                    b[1] = float(self.h - 2.2)
                    offset = (b[0] - (self.px + self.paddle_w / 2.0)) / (self.paddle_w / 2.0)
                    b[2] = max(-0.85, min(0.85, offset * 0.75))
                    b[3] = -abs(b[3])

            # Brick collision (rows 1..5 map to brick r 0..4)
            by_i = int(round(b[1]))
            bx_i = int(round(b[0]))
            if 1 <= by_i <= 5 and 1 <= bx_i <= 50:
                br = by_i - 1
                bc = (bx_i - 1) // self.brick_w
                if (br, bc) in self.bricks:
                    self.bricks[(br, bc)] -= 1
                    b[3] = -b[3]
                    if self.bricks[(br, bc)] <= 0:
                        del self.bricks[(br, bc)]
                        self.score += (5 - br) * 10
                        if self.score > self.scores.get("bricks_high", 0):
                            self.scores["bricks_high"] = self.score
                            save_scores(self.scores)
                        if random.random() < 0.18:
                            self.powerups.append([float(bx_i), float(by_i), random.choice(["W", "M", "+"])])

            if b[1] < self.h:
                active_balls.append(b)

        self.balls = active_balls
        if not self.balls:
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                self.paddle_w = 9
                self.balls = [[self.px + self.paddle_w / 2.0, float(self.h - 2), 0.55, -0.55]]

        # Update falling power-ups
        new_pu = []
        for pu in self.powerups:
            pu[1] += 0.28
            if pu[1] >= self.h - 1.5 and self.px - 1 <= pu[0] <= self.px + self.paddle_w + 1:
                if pu[2] == "W":
                    self.paddle_w = min(15, self.paddle_w + 3)
                elif pu[2] == "M" and self.balls:
                    bx, by, _, _ = self.balls[0]
                    self.balls.append([bx, by, -0.45, -0.55])
                    self.balls.append([bx, by, 0.45, -0.55])
                elif pu[2] == "+":
                    self.lives = min(5, self.lives + 1)
            elif pu[1] < self.h:
                new_pu.append(pu)
        self.powerups = new_pu

        if not self.bricks:
            self.level += 1
            self.score += 200
            self.setup_level()

    def render(self) -> list[str]:
        box_w = 78
        hearts = f"{Style.FG_RED}{'♥' * self.lives}{Style.RESET}"
        header = (
            f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<6}{Style.RESET}   "
            f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores.get('bricks_high', 0):<6}{Style.RESET}   "
            f"{Style.BOLD}LEVEL:{Style.RESET} {Style.FG_CYAN}{self.level:<3}{Style.RESET}   "
            f"{Style.BOLD}BALLS:{Style.RESET} {hearts}"
        )
        body = [
            pad_center(header, box_w - 2),
            pad_center(f"{Style.DIM}Power-ups: [W] Wide Paddle   [M] Multi-Ball   [+] Extra Ball{Style.RESET}", box_w - 2),
            pad_center(f"{Style.FG_MAGENTA}┌{'─' * self.w}┐{Style.RESET}", box_w - 2),
        ]

        grid = [[" " for _ in range(self.w)] for _ in range(self.h)]

        # Draw bricks
        for (br, bc), hp in self.bricks.items():
            ry = br + 1
            start_x = 1 + bc * self.brick_w
            col = self.ROW_COLORS[br % len(self.ROW_COLORS)]
            ch = "▓" if hp > 1 else "█"
            for dx in range(self.brick_w - 1):
                if start_x + dx < self.w:
                    grid[ry][start_x + dx] = f"{col}{Style.BOLD}{ch}{Style.RESET}"

        # Draw power-ups
        for px, py, kind in self.powerups:
            ix, iy = int(round(px)), int(round(py))
            if 0 <= iy < self.h and 1 <= ix < self.w - 1:
                grid[iy][ix - 1] = f"{Style.FG_GOLD}{Style.BOLD}[{Style.RESET}"
                grid[iy][ix] = f"{Style.FG_GOLD}{Style.BOLD}{kind}{Style.RESET}"
                grid[iy][ix + 1] = f"{Style.FG_GOLD}{Style.BOLD}]{Style.RESET}"

        # Draw paddle
        p_start = int(round(self.px))
        for dx in range(self.paddle_w):
            cx = p_start + dx
            if 0 <= cx < self.w:
                grid[self.h - 1][cx] = f"{Style.FG_CYAN}{Style.BOLD}═{Style.RESET}"

        # Draw balls
        for bx, by, _, _ in self.balls:
            ix, iy = int(round(bx)), int(round(by))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{Style.FG_WHITE}{Style.BOLD}●{Style.RESET}"

        for r in range(self.h):
            row_str = "".join(grid[r])
            if self.game_over and r in (self.h // 2 - 1, self.h // 2):
                if r == self.h // 2 - 1:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}   !! GAME OVER — FINAL SCORE: {self.score:<6} !!   {Style.RESET}"
                else:
                    msg = f"{Style.BG_ALERT}{Style.FG_GOLD}{Style.BOLD}   Press [ENTER/R] to Replay or [Q] Menu   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            elif self.paused and r == self.h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P/SPACE] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, self.w)

            body.append(pad_center(f"{Style.FG_MAGENTA}│{Style.RESET}{row_str}{Style.FG_MAGENTA}│{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{Style.FG_MAGENTA}└{'─' * self.w}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[◄/► or A/D]{Style.RESET} Paddle  "
            f"{Style.FG_YELLOW}[P/Space]{Style.RESET} Pause  "
            f"{Style.FG_YELLOW}[R]{Style.RESET} Restart  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ BRICK BREAKER ARKANOID ★", body, box_w, Style.FG_MAGENTA)

    def run(self):
        self.reset()
        last_step = time.perf_counter()
        while True:
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            now = time.perf_counter()
            if now - last_step >= 0.032:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.012)


# ============================================================================
# GAME 8: CYBERWING (R-TYPE HORIZONTAL SHOOT 'EM UP) TUI
# ============================================================================

class CyberWingShmupGame:
    """Horizontal side-scrolling R-Type / Gradius style Shoot 'Em Up with SHIFT Phase-Dodge."""

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.w = 58
        self.h = 15
        self.auto_fire = True
        self.reset()

    def reset(self):
        self.px = 6
        self.py = self.h // 2
        self.last_dir = (0, -1)
        self.lives = 3
        self.weapon_lv = 1
        self.has_drone = True
        self.bombs = 2
        self.score = 0
        self.sector = 1
        self.kills_in_sector = 0
        self.ticks = 0
        self.fire_cd = 0
        self.invuln_ticks = 0
        self.dodge_cd = 0
        self.dodge_active = 0
        self.graze_ticks = 0
        self.shift_was_down = False
        self.paused = False
        self.game_over = False

        self.bullets = []        # [x, y, vx, vy, ch, col]
        self.enemy_bullets = []  # [x, y, vx, vy]
        self.enemies = []        # dict: x, y, vy, hp, max_hp, kind, timer
        self.powerups = []       # [x, y, kind]
        self.particles = []      # [x, y, ttl, ch, col]
        self.stars = [
            [random.randint(0, self.w - 1), random.randint(1, self.h - 2), random.choice([1, 2])]
            for _ in range(20)
        ]

    def trigger_dodge(self):
        """Evasive horizontal/vertical Phase-Boost on SHIFT."""
        if self.dodge_cd > 0 or self.paused or self.game_over:
            return
        self.dodge_cd = 15
        self.dodge_active = 7
        self.invuln_ticks = max(self.invuln_ticks, 9)

        dx, dy = self.last_dir
        if dx == 0 and dy == 0:
            dy = -1

        steps = 6 if dx != 0 else 4
        grazed = 0
        for s in range(1, steps + 1):
            col = Style.FG_MAGENTA if s % 2 == 0 else Style.FG_CYAN
            self.particles.append([float(self.px - 1), float(self.py), 4, "═", col])
            self.particles.append([float(self.px), float(self.py), 4, "►", col])
            self.px = max(3, min(self.w - 10, self.px + dx))
            self.py = max(1, min(self.h - 2, self.py + dy))

            surviving_eb = []
            for eb in self.enemy_bullets:
                if abs(eb[0] - self.px) <= 2.4 and abs(eb[1] - self.py) <= 1.6:
                    grazed += 1
                    self.particles.append([eb[0], eb[1], 3, "*", Style.FG_GOLD])
                else:
                    surviving_eb.append(eb)
            self.enemy_bullets = surviving_eb

        if grazed > 0:
            self.score += grazed * 30
            self.graze_ticks = 16
            if self.score > self.scores.get("cyberwing_high", 0):
                self.scores["cyberwing_high"] = self.score
                save_scores(self.scores)

    def fire_weapons(self):
        if self.fire_cd > 0:
            return
        self.fire_cd = 3
        # Main plasma beam
        self.bullets.append([float(self.px + 2), float(self.py), 1.4, 0.0, "═", Style.FG_CYAN])
        if self.weapon_lv >= 2:
            # Wave beam + twin shot
            self.bullets.append([float(self.px + 2), float(max(1, self.py - 1)), 1.35, -0.08, "≈", Style.FG_GOLD])
        if self.weapon_lv >= 3:
            # Homing / Spread missiles
            self.bullets.append([float(self.px + 1), float(min(self.h - 2, self.py + 1)), 1.25, 0.12, "►", Style.FG_MAGENTA])
        # Orbital Option Drone fire
        if self.has_drone and self.ticks % 2 == 0:
            dy_drone = -2 if self.py > 3 else 2
            self.bullets.append([float(self.px), float(self.py + dy_drone), 1.35, 0.0, "─", Style.FG_LIME])

    def trigger_bomb(self):
        if self.bombs <= 0 or self.paused or self.game_over:
            return
        self.bombs -= 1
        self.enemy_bullets.clear()
        survivors = []
        for e in self.enemies:
            e["hp"] -= 18
            if e["hp"] <= 0:
                self._on_enemy_killed(e)
            else:
                survivors.append(e)
        self.enemies = survivors

    def _on_enemy_killed(self, e: dict):
        pts = {"DRONE": 25, "MECH": 55, "TURRET": 70, "CORE_BOSS": 600}.get(e["kind"], 30)
        self.score += pts
        self.kills_in_sector += 1
        if self.score > self.scores.get("cyberwing_high", 0):
            self.scores["cyberwing_high"] = self.score
            save_scores(self.scores)

        for _ in range(8 if e["kind"] != "CORE_BOSS" else 20):
            self.particles.append([
                e["x"] + random.randint(-2, 2),
                e["y"] + random.randint(-1, 1),
                random.randint(3, 6),
                random.choice(["*", "#", "+"]),
                random.choice([Style.FG_GOLD, Style.FG_RED, Style.FG_ORANGE]),
            ])

        if random.random() < (1.0 if e["kind"] == "CORE_BOSS" else 0.16):
            self.powerups.append([e["x"], e["y"], random.choice(["W", "B", "+"])])

        if e["kind"] == "CORE_BOSS":
            self.sector += 1
            self.kills_in_sector = 0

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key == "P":
            self.paused = not self.paused
            return True
        if key in ("F", "M", "TAB"):
            self.auto_fire = not self.auto_fire
            return True
        if key in ("B", "X"):
            self.trigger_bomb()
            return True
        if key in ("SHIFT", "C"):
            self.trigger_dodge()
            return True
        if key in ("ENTER", "SPACE") and self.game_over:
            self.reset()
            return True

        if not self.paused and not self.game_over:
            if key in ("SPACE", "Z"):
                self.fire_weapons()
            if not (
                self.term.is_key_down("LEFT") or self.term.is_key_down("RIGHT")
                or self.term.is_key_down("UP") or self.term.is_key_down("DOWN")
                or self.term.is_key_down("A") or self.term.is_key_down("D")
                or self.term.is_key_down("W") or self.term.is_key_down("S")
            ):
                if key == "LEFT":
                    self.last_dir = (-1, 0)
                    self.px = max(3, self.px - 2)
                elif key == "RIGHT":
                    self.last_dir = (1, 0)
                    self.px = min(self.w - 12, self.px + 2)
                elif key == "UP":
                    self.last_dir = (0, -1)
                    self.py = max(1, self.py - 1)
                elif key == "DOWN":
                    self.last_dir = (0, 1)
                    self.py = min(self.h - 2, self.py + 1)
        return True

    def step(self):
        if self.paused or self.game_over:
            return

        self.ticks += 1
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.dodge_cd > 0:
            self.dodge_cd -= 1
        if self.dodge_active > 0:
            self.dodge_active -= 1
        if self.graze_ticks > 0:
            self.graze_ticks -= 1

        mx, my = 0, 0
        if self.term.is_key_down("LEFT") or self.term.is_key_down("A"):
            mx -= 1
        if self.term.is_key_down("RIGHT") or self.term.is_key_down("D"):
            mx += 1
        if self.term.is_key_down("UP") or self.term.is_key_down("W"):
            my -= 1
        if self.term.is_key_down("DOWN") or self.term.is_key_down("S"):
            my += 1

        if mx != 0 or my != 0:
            self.last_dir = (mx, my)
            self.px = max(3, min(self.w - 12, self.px + mx))
            self.py = max(1, min(self.h - 2, self.py + my))

        shift_now = self.term.is_key_down("SHIFT") or self.term.is_key_down("C")
        if shift_now and not self.shift_was_down:
            self.trigger_dodge()
        self.shift_was_down = shift_now

        if self.auto_fire or self.term.is_key_down("SPACE") or self.term.is_key_down("Z"):
            self.fire_weapons()

        # Scroll horizontal stars
        for s in self.stars:
            s[0] = (s[0] - s[2]) % self.w

        # Spawn enemies or Core Boss
        has_boss = any(e["kind"] == "CORE_BOSS" for e in self.enemies)
        if not has_boss:
            if self.kills_in_sector >= 12 + self.sector * 3:
                boss_hp = 30 + self.sector * 12
                self.enemies.append({
                    "x": float(self.w - 6),
                    "y": float(self.h // 2),
                    "vy": 0.35,
                    "hp": boss_hp,
                    "max_hp": boss_hp,
                    "kind": "CORE_BOSS",
                    "timer": 0,
                })
            elif self.ticks % max(12, 26 - self.sector * 2) == 0 and len(self.enemies) < 7:
                kind = random.choice(["DRONE", "DRONE", "MECH", "TURRET"])
                ey = (self.h - 2) if kind == "TURRET" else random.randint(2, self.h - 3)
                hp = {"DRONE": 1, "MECH": 3 + self.sector // 2, "TURRET": 3}.get(kind, 2)
                self.enemies.append({
                    "x": float(self.w - 2),
                    "y": float(ey),
                    "vy": 0.25 if kind == "DRONE" else 0.0,
                    "hp": hp,
                    "max_hp": hp,
                    "kind": kind,
                    "timer": 0,
                })

        # Update player bullets
        new_b = []
        for b in self.bullets:
            b[0] += b[2]
            b[1] += b[3]
            if 0 <= b[0] < self.w and 1 <= b[1] < self.h - 1:
                new_b.append(b)
        self.bullets = new_b

        # Update enemies
        surviving = []
        for e in self.enemies:
            e["timer"] += 1
            if e["kind"] == "DRONE":
                e["x"] -= 0.45
                e["y"] = max(1.5, min(float(self.h - 2.5), e["y"] + math.sin(e["timer"] * 0.2) * 0.35))
            elif e["kind"] == "MECH":
                e["x"] -= 0.28
                if e["timer"] % 22 == 0:
                    self.enemy_bullets.append([e["x"] - 1, e["y"], -0.75, 0.0])
            elif e["kind"] == "TURRET":
                e["x"] -= 0.22
                if e["timer"] % 24 == 0:
                    dy = -0.25 if self.py < e["y"] else 0.0
                    self.enemy_bullets.append([e["x"] - 1, e["y"] - 0.5, -0.65, dy])
            elif e["kind"] == "CORE_BOSS":
                e["y"] += e["vy"]
                if e["y"] <= 3.0 or e["y"] >= self.h - 4.0:
                    e["vy"] = -e["vy"]
                if e["timer"] % 12 == 0:
                    for vy in (-0.22, 0.0, 0.22):
                        self.enemy_bullets.append([e["x"] - 3, e["y"], -0.75, vy])

            # Check bullet hits
            hit_w = 3.5 if e["kind"] == "CORE_BOSS" else 1.8
            hit_h = 2.2 if e["kind"] == "CORE_BOSS" else 1.1
            rem_b = []
            for b in self.bullets:
                if abs(b[0] - e["x"]) <= hit_w and abs(b[1] - e["y"]) <= hit_h:
                    e["hp"] -= 1
                    self.particles.append([b[0], b[1], 2, "+", Style.FG_YELLOW])
                else:
                    rem_b.append(b)
            self.bullets = rem_b

            # Check player collision with enemy ship
            if abs(e["x"] - self.px) <= 1.8 and abs(e["y"] - self.py) <= 1.0:
                self._hit_player()

            if e["hp"] <= 0:
                self._on_enemy_killed(e)
            elif e["x"] > 0:
                surviving.append(e)
        self.enemies = surviving

        # Update enemy bullets
        new_eb = []
        for eb in self.enemy_bullets:
            eb[0] += eb[2]
            eb[1] += eb[3]
            if 0 <= eb[0] < self.w and 1 <= eb[1] < self.h - 1:
                if abs(eb[0] - self.px) <= 1.4 and abs(eb[1] - self.py) <= 0.9:
                    self._hit_player()
                else:
                    new_eb.append(eb)
        self.enemy_bullets = new_eb

        # Update power-ups
        new_pu = []
        for pu in self.powerups:
            pu[0] -= 0.3
            if abs(pu[0] - self.px) <= 2.0 and abs(pu[1] - self.py) <= 1.3:
                if pu[2] == "W":
                    self.weapon_lv = min(3, self.weapon_lv + 1)
                elif pu[2] == "B":
                    self.bombs = min(5, self.bombs + 1)
                elif pu[2] == "+":
                    self.lives = min(5, self.lives + 1)
            elif pu[0] > 0:
                new_pu.append(pu)
        self.powerups = new_pu

        self.particles = [[p[0], p[1], p[2] - 1, p[3], p[4]] for p in self.particles if p[2] > 1]

    def _hit_player(self):
        if self.invuln_ticks > 0 or self.dodge_active > 0:
            return
        self.lives -= 1
        self.weapon_lv = max(1, self.weapon_lv - 1)
        self.invuln_ticks = 22
        if self.lives <= 0:
            self.game_over = True

    def render(self) -> list[str]:
        box_w = 84
        hearts = f"{Style.FG_RED}{'♥' * self.lives}{Style.RESET}"
        dodge_str = (
            f"{Style.FG_LIME}READY{Style.RESET}"
            if self.dodge_cd == 0
            else f"{Style.FG_YELLOW}CD:{self.dodge_cd:<2}{Style.RESET}"
        )
        header = (
            f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<6}{Style.RESET} "
            f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores.get('cyberwing_high', 0):<6}{Style.RESET} "
            f"{Style.BOLD}SECTOR:{Style.RESET} {Style.FG_CYAN}{self.sector:<2}{Style.RESET} "
            f"{Style.BOLD}HULL:{Style.RESET} {hearts}  "
            f"{Style.BOLD}DODGE:{Style.RESET} {dodge_str}  "
            f"{Style.BOLD}WPN:{Style.RESET} {Style.FG_YELLOW}Lv.{self.weapon_lv}{Style.RESET}  "
            f"{Style.BOLD}EMP:{Style.RESET} {Style.FG_ORANGE}{'★' * self.bombs}{Style.RESET}"
        )
        body = [pad_center(header, box_w - 2)]

        boss = next((e for e in self.enemies if e["kind"] == "CORE_BOSS"), None)
        if boss:
            filled = max(0, int((boss["hp"] / boss["max_hp"]) * 26))
            body.append(
                pad_center(
                    f"{Style.FG_RED}{Style.BOLD}CORE BATTLESHIP: [{'█' * filled}{'·' * (26 - filled)}] {boss['hp']}/{boss['max_hp']}{Style.RESET}",
                    box_w - 2,
                )
            )
        elif self.graze_ticks > 0:
            body.append(pad_center(f"{Style.FG_GOLD}{Style.BOLD}★ PHASE-BOOST GRAZE DODGE! +30 PTS ★{Style.RESET}", box_w - 2))
        else:
            body.append(
                pad_center(
                    f"{Style.DIM}Option Drone: ACTIVE  |  Press [SHIFT] to Phase-Boost Dodge through Bullets!{Style.RESET}",
                    box_w - 2,
                )
            )

        border_col = Style.FG_MAGENTA if self.dodge_active > 0 else Style.FG_CYAN
        body.append(pad_center(f"{border_col}┌{'─' * self.w}┐{Style.RESET}", box_w - 2))

        grid = [[" " for _ in range(self.w)] for _ in range(self.h)]

        # Canyon ceiling & floor terrain
        for c in range(self.w):
            t_char = "▀" if (c + self.ticks) % 4 != 0 else "▓"
            b_char = "▄" if (c + self.ticks) % 4 != 0 else "▓"
            grid[0][c] = f"{Style.FG_PURPLE}{t_char}{Style.RESET}"
            grid[self.h - 1][c] = f"{Style.FG_PURPLE}{b_char}{Style.RESET}"

        for sx, sy, spd in self.stars:
            if 0 <= sx < self.w and 1 <= sy < self.h - 1:
                grid[sy][sx] = f"{Style.FG_GRAY}{'·' if spd == 2 else '.'}{Style.RESET}"

        for px, py, kind in self.powerups:
            ix, iy = int(round(px)), int(round(py))
            if 1 <= iy < self.h - 1 and 1 <= ix < self.w - 1:
                grid[iy][ix - 1] = f"{Style.FG_GOLD}{Style.BOLD}[{Style.RESET}"
                grid[iy][ix] = f"{Style.FG_GOLD}{Style.BOLD}{kind}{Style.RESET}"
                grid[iy][ix + 1] = f"{Style.FG_GOLD}{Style.BOLD}]{Style.RESET}"

        for bx, by, _, _, bch, bcol in self.bullets:
            ix, iy = int(round(bx)), int(round(by))
            if 0 <= ix < self.w and 1 <= iy < self.h - 1:
                grid[iy][ix] = f"{bcol}{Style.BOLD}{bch}{Style.RESET}"

        for ebx, eby, _, _ in self.enemy_bullets:
            ix, iy = int(round(ebx)), int(round(eby))
            if 0 <= ix < self.w and 1 <= iy < self.h - 1:
                grid[iy][ix] = f"{Style.FG_RED}{Style.BOLD}•{Style.RESET}"

        for e in self.enemies:
            ix, iy = int(round(e["x"])), int(round(e["y"]))
            if not (1 <= iy < self.h - 1):
                continue
            if e["kind"] == "DRONE":
                sprite, col = "◄●►", Style.FG_GREEN
            elif e["kind"] == "MECH":
                sprite, col = "◄██╣", Style.FG_RED
            elif e["kind"] == "TURRET":
                sprite, col = "╔╩╗", Style.FG_ORANGE
            else:
                sprite, col = "◄╠██◎██╣", Style.FG_GOLD
            half = len(sprite) // 2
            for idx, ch in enumerate(sprite):
                cx = ix - half + idx
                if 0 <= cx < self.w:
                    grid[iy][cx] = f"{col}{Style.BOLD}{ch}{Style.RESET}"

        for px, py, _, pch, pcol in self.particles:
            ix, iy = int(round(px)), int(round(py))
            if 0 <= ix < self.w and 1 <= iy < self.h - 1:
                grid[iy][ix] = f"{pcol}{Style.BOLD}{pch}{Style.RESET}"

        # Player CyberWing Fighter + Option Drone
        if not self.game_over and (self.invuln_ticks % 2 == 0 or self.dodge_active > 0):
            ship = "»╦►" if self.dodge_active > 0 else "═╦►"
            scol = Style.FG_MAGENTA if self.dodge_active > 0 else Style.FG_CYAN
            for idx, ch in enumerate(ship):
                cx = self.px - 1 + idx
                if 0 <= cx < self.w and 1 <= self.py < self.h - 1:
                    grid[self.py][cx] = f"{scol}{Style.BOLD}{ch}{Style.RESET}"

            if self.has_drone:
                dy_drone = -2 if self.py > 3 else 2
                ry = self.py + dy_drone
                if 1 <= ry < self.h - 1 and 0 <= self.px < self.w:
                    grid[ry][self.px] = f"{Style.FG_LIME}{Style.BOLD}◎{Style.RESET}"

        for r in range(self.h):
            row_str = "".join(grid[r])
            if self.game_over and r in (self.h // 2 - 1, self.h // 2):
                if r == self.h // 2 - 1:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}  !! CYBERWING DOWN — SCORE: {self.score:<6} !!  {Style.RESET}"
                else:
                    msg = f"{Style.BG_ALERT}{Style.FG_GOLD}{Style.BOLD}   Press [ENTER/R] to Sortie or [Q] Menu   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            elif self.paused and r == self.h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            body.append(pad_center(f"{border_col}│{Style.RESET}{row_str}{border_col}│{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{border_col}└{'─' * self.w}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[WASD/Arrows]{Style.RESET} Fly  "
            f"{Style.FG_YELLOW}[SHIFT]{Style.RESET} Dodge  "
            f"{Style.FG_YELLOW}[Space]{Style.RESET} Fire  "
            f"{Style.FG_YELLOW}[B]{Style.RESET} EMP  "
            f"{Style.FG_YELLOW}[F]{Style.RESET} AutoFire  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ CYBERWING: R-TYPE HORIZONTAL SHMUP ★", body, box_w, Style.FG_CYAN)

    def run(self):
        self.reset()
        last_step = time.perf_counter()
        while True:
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            now = time.perf_counter()
            if now - last_step >= 0.038:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.012)


# ============================================================================
# GAME 9: NEON OVERDRIVE (360° BULLET-HELL ARENA SHMUP) TUI
# ============================================================================

class NeonArenaShmupGame:
    """Top-down 360-degree Twin-Stick / Bullet-Hell Arena Shoot 'Em Up with SHIFT Blink-Dodge."""

    def __init__(self, term: Terminal, scores: dict):
        self.term = term
        self.scores = scores
        self.w = 54
        self.h = 15
        self.auto_aim = True
        self.reset()

    def reset(self):
        self.px = float(self.w // 2)
        self.py = float(self.h // 2)
        self.aim_dir = (1.0, 0.0)
        self.lives = 3
        self.bombs = 2
        self.score = 0
        self.wave = 1
        self.kills = 0
        self.ticks = 0
        self.fire_cd = 0
        self.invuln_ticks = 0
        self.dodge_cd = 0
        self.dodge_active = 0
        self.graze_ticks = 0
        self.shift_was_down = False
        self.paused = False
        self.game_over = False

        self.bullets = []        # [x, y, vx, vy]
        self.enemy_bullets = []  # [x, y, vx, vy]
        self.enemies = []        # dict: x, y, hp, kind, timer
        self.particles = []      # [x, y, ttl, ch, col]

    def trigger_dodge(self):
        """360-degree Phase Blink-Dash on SHIFT: phases through bullets & damages enemies along dash!"""
        if self.dodge_cd > 0 or self.paused or self.game_over:
            return
        self.dodge_cd = 15
        self.dodge_active = 8
        self.invuln_ticks = max(self.invuln_ticks, 10)

        dx, dy = self.aim_dir
        mag = math.hypot(dx, dy) or 1.0
        ux, uy = dx / mag, dy / mag

        grazed = 0
        for s in range(1, 7):
            col = Style.FG_MAGENTA if s % 2 == 0 else Style.FG_CYAN
            self.particles.append([self.px, self.py, 5, "◈", col])
            self.px = max(2.0, min(float(self.w - 3), self.px + ux * 1.4))
            self.py = max(1.0, min(float(self.h - 2), self.py + uy * 0.9))

            # Clear enemy bullets grazed during blink-dash
            rem_eb = []
            for eb in self.enemy_bullets:
                if math.hypot(eb[0] - self.px, eb[1] - self.py) <= 2.3:
                    grazed += 1
                    self.particles.append([eb[0], eb[1], 3, "*", Style.FG_GOLD])
                else:
                    rem_eb.append(eb)
            self.enemy_bullets = rem_eb

            # Dash shockwave damages enemies passed through
            for e in self.enemies:
                if math.hypot(e["x"] - self.px, e["y"] - self.py) <= 2.2:
                    e["hp"] -= 2

        if grazed > 0:
            self.score += grazed * 25
            self.graze_ticks = 16
            if self.score > self.scores.get("arena_shmup_high", 0):
                self.scores["arena_shmup_high"] = self.score
                save_scores(self.scores)

    def fire_turret(self):
        if self.fire_cd > 0:
            return
        self.fire_cd = 3

        # Auto-aim at nearest enemy or use movement direction
        vx, vy = self.aim_dir
        if self.auto_aim and self.enemies:
            nearest = min(self.enemies, key=lambda e: math.hypot(e["x"] - self.px, e["y"] - self.py))
            dx = nearest["x"] - self.px
            dy = (nearest["y"] - self.py) * 1.6
            dist = math.hypot(dx, dy) or 1.0
            vx, vy = (dx / dist) * 1.35, (dy / dist) * 0.75
        else:
            dist = math.hypot(vx, vy) or 1.0
            vx, vy = (vx / dist) * 1.35, (vy / dist) * 0.75

        self.bullets.append([self.px, self.py, vx, vy])
        if self.wave >= 2:
            # Twin spread
            self.bullets.append([self.px, self.py, vx * 0.95 - vy * 0.2, vy * 0.95 + vx * 0.1])

    def trigger_nova(self):
        if self.bombs <= 0 or self.paused or self.game_over:
            return
        self.bombs -= 1
        self.enemy_bullets.clear()
        for angle_deg in range(0, 360, 20):
            rad = math.radians(angle_deg)
            self.bullets.append([self.px, self.py, math.cos(rad) * 1.3, math.sin(rad) * 0.7])
        for e in self.enemies:
            e["hp"] -= 10

    def handle_input(self, key: str) -> bool:
        if key in ("ESC", "Q"):
            return False
        if key == "R":
            self.reset()
            return True
        if key == "P":
            self.paused = not self.paused
            return True
        if key in ("F", "M", "TAB"):
            self.auto_aim = not self.auto_aim
            return True
        if key in ("B", "X"):
            self.trigger_nova()
            return True
        if key in ("SHIFT", "C"):
            self.trigger_dodge()
            return True
        if key in ("ENTER", "SPACE") and self.game_over:
            self.reset()
            return True

        if not self.paused and not self.game_over:
            if key in ("SPACE", "Z"):
                self.fire_turret()
            if not (
                self.term.is_key_down("LEFT") or self.term.is_key_down("RIGHT")
                or self.term.is_key_down("UP") or self.term.is_key_down("DOWN")
                or self.term.is_key_down("A") or self.term.is_key_down("D")
                or self.term.is_key_down("W") or self.term.is_key_down("S")
            ):
                if key == "LEFT":
                    self.aim_dir = (-1.0, 0.0)
                    self.px = max(2.0, self.px - 2.0)
                elif key == "RIGHT":
                    self.aim_dir = (1.0, 0.0)
                    self.px = min(float(self.w - 3), self.px + 2.0)
                elif key == "UP":
                    self.aim_dir = (0.0, -1.0)
                    self.py = max(1.0, self.py - 1.0)
                elif key == "DOWN":
                    self.aim_dir = (0.0, 1.0)
                    self.py = min(float(self.h - 2), self.py + 1.0)
        return True

    def step(self):
        if self.paused or self.game_over:
            return

        self.ticks += 1
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.dodge_cd > 0:
            self.dodge_cd -= 1
        if self.dodge_active > 0:
            self.dodge_active -= 1
        if self.graze_ticks > 0:
            self.graze_ticks -= 1

        mx, my = 0.0, 0.0
        if self.term.is_key_down("LEFT") or self.term.is_key_down("A"):
            mx -= 1.15
        if self.term.is_key_down("RIGHT") or self.term.is_key_down("D"):
            mx += 1.15
        if self.term.is_key_down("UP") or self.term.is_key_down("W"):
            my -= 0.75
        if self.term.is_key_down("DOWN") or self.term.is_key_down("S"):
            my += 0.75

        if mx != 0.0 or my != 0.0:
            self.aim_dir = (mx, my)
            self.px = max(2.0, min(float(self.w - 3), self.px + mx))
            self.py = max(1.0, min(float(self.h - 2), self.py + my))

        shift_now = self.term.is_key_down("SHIFT") or self.term.is_key_down("C")
        if shift_now and not self.shift_was_down:
            self.trigger_dodge()
        self.shift_was_down = shift_now

        self.fire_turret()

        # Spawn perimeter swarm enemies
        if self.ticks % max(10, 24 - self.wave * 2) == 0 and len(self.enemies) < 8 + self.wave:
            edge = random.choice(["TOP", "BOTTOM", "LEFT", "RIGHT"])
            if edge == "TOP":
                ex, ey = float(random.randint(3, self.w - 4)), 1.0
            elif edge == "BOTTOM":
                ex, ey = float(random.randint(3, self.w - 4)), float(self.h - 2)
            elif edge == "LEFT":
                ex, ey = 2.0, float(random.randint(2, self.h - 3))
            else:
                ex, ey = float(self.w - 3), float(random.randint(2, self.h - 3))

            kind = random.choice(["SEEKER", "SEEKER", "SPINNER", "TANK"])
            hp = {"SEEKER": 1, "SPINNER": 2 + self.wave // 2, "TANK": 5 + self.wave}.get(kind, 2)
            self.enemies.append({"x": ex, "y": ey, "hp": hp, "kind": kind, "timer": 0})

        # Update bullets
        new_b = []
        for b in self.bullets:
            b[0] += b[2]
            b[1] += b[3]
            if 0 <= b[0] < self.w and 0 <= b[1] < self.h:
                new_b.append(b)
        self.bullets = new_b

        # Update enemies
        surviving = []
        for e in self.enemies:
            e["timer"] += 1
            dx = self.px - e["x"]
            dy = self.py - e["y"]
            dist = math.hypot(dx, dy) or 1.0
            spd = 0.36 if e["kind"] == "SEEKER" else (0.18 if e["kind"] == "TANK" else 0.24)
            e["x"] += (dx / dist) * spd
            e["y"] += (dy / dist) * (spd * 0.65)

            # Spinner fires radial bullet-hell rings
            if e["kind"] == "SPINNER" and e["timer"] % 22 == 0:
                for deg in (0, 90, 180, 270):
                    rad = math.radians(deg + e["timer"] * 7)
                    self.enemy_bullets.append([e["x"], e["y"], math.cos(rad) * 0.65, math.sin(rad) * 0.38])
            elif e["kind"] == "TANK" and e["timer"] % 26 == 0:
                self.enemy_bullets.append([e["x"], e["y"], (dx / dist) * 0.72, (dy / dist) * 0.42])

            rem_b = []
            for b in self.bullets:
                if abs(b[0] - e["x"]) <= 1.7 and abs(b[1] - e["y"]) <= 1.1:
                    e["hp"] -= 1
                    self.particles.append([b[0], b[1], 2, "+", Style.FG_YELLOW])
                else:
                    rem_b.append(b)
            self.bullets = rem_b

            if abs(e["x"] - self.px) <= 1.4 and abs(e["y"] - self.py) <= 0.9:
                self._hit_player()

            if e["hp"] <= 0:
                pts = {"SEEKER": 20, "SPINNER": 45, "TANK": 90}.get(e["kind"], 25)
                self.score += pts
                self.kills += 1
                if self.kills % 15 == 0:
                    self.wave += 1
                if self.score > self.scores.get("arena_shmup_high", 0):
                    self.scores["arena_shmup_high"] = self.score
                    save_scores(self.scores)
                for _ in range(6):
                    self.particles.append([
                        e["x"] + random.uniform(-1.5, 1.5),
                        e["y"] + random.uniform(-1.0, 1.0),
                        4, "*", random.choice([Style.FG_PINK, Style.FG_CYAN, Style.FG_GOLD]),
                    ])
            else:
                surviving.append(e)
        self.enemies = surviving

        # Update enemy bullets
        new_eb = []
        for eb in self.enemy_bullets:
            eb[0] += eb[2]
            eb[1] += eb[3]
            if 0 <= eb[0] < self.w and 0 <= eb[1] < self.h:
                if abs(eb[0] - self.px) <= 1.2 and abs(eb[1] - self.py) <= 0.8:
                    self._hit_player()
                else:
                    new_eb.append(eb)
        self.enemy_bullets = new_eb

        self.particles = [[p[0], p[1], p[2] - 1, p[3], p[4]] for p in self.particles if p[2] > 1]

    def _hit_player(self):
        if self.invuln_ticks > 0 or self.dodge_active > 0:
            return
        self.lives -= 1
        self.invuln_ticks = 22
        if self.lives <= 0:
            self.game_over = True

    def render(self) -> list[str]:
        box_w = 86
        hearts = f"{Style.FG_RED}{'♥' * self.lives}{Style.RESET}"
        dodge_str = (
            f"{Style.FG_LIME}READY{Style.RESET}"
            if self.dodge_cd == 0
            else f"{Style.FG_YELLOW}CD:{self.dodge_cd:<2}{Style.RESET}"
        )
        aim_mode = f"{Style.FG_GREEN}AUTO-AIM{Style.RESET}" if self.auto_aim else f"{Style.FG_CYAN}8-WAY DIR{Style.RESET}"

        header = (
            f"{Style.BOLD}SCORE:{Style.RESET} {Style.FG_GREEN}{self.score:<6}{Style.RESET} "
            f"{Style.BOLD}BEST:{Style.RESET} {Style.FG_GOLD}{self.scores.get('arena_shmup_high', 0):<6}{Style.RESET} "
            f"{Style.BOLD}WAVE:{Style.RESET} {Style.FG_CYAN}{self.wave:<2}{Style.RESET} "
            f"{Style.BOLD}HULL:{Style.RESET} {hearts}  "
            f"{Style.BOLD}DODGE:{Style.RESET} {dodge_str}  "
            f"{Style.BOLD}AIM:{Style.RESET} {aim_mode}  "
            f"{Style.BOLD}NOVA:{Style.RESET} {Style.FG_ORANGE}{'★' * self.bombs}{Style.RESET}"
        )
        body = [pad_center(header, box_w - 2)]

        if self.graze_ticks > 0:
            body.append(pad_center(f"{Style.FG_GOLD}{Style.BOLD}★ BLINK-DODGE GRAZE SHOCKWAVE! +25 PTS ★{Style.RESET}", box_w - 2))
        else:
            body.append(
                pad_center(
                    f"{Style.DIM}360° Bullet-Hell Arena — Press [SHIFT] to Blink-Dodge through Bullets & Enemies!{Style.RESET}",
                    box_w - 2,
                )
            )

        border_col = Style.FG_MAGENTA if self.dodge_active > 0 else Style.FG_PINK
        body.append(pad_center(f"{border_col}┌{'─' * self.w}┐{Style.RESET}", box_w - 2))

        grid = [[" " for _ in range(self.w)] for _ in range(self.h)]

        # Subtle arena floor grid dots
        for r in range(1, self.h - 1, 3):
            for c in range(3, self.w - 3, 6):
                grid[r][c] = f"{Style.FG_GRAY}·{Style.RESET}"

        for bx, by, _, _ in self.bullets:
            ix, iy = int(round(bx)), int(round(by))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{Style.FG_CYAN}{Style.BOLD}•{Style.RESET}"

        for ebx, eby, _, _ in self.enemy_bullets:
            ix, iy = int(round(ebx)), int(round(eby))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{Style.FG_RED}{Style.BOLD}*{Style.RESET}"

        for e in self.enemies:
            ix, iy = int(round(e["x"])), int(round(e["y"]))
            if not (0 <= iy < self.h):
                continue
            if e["kind"] == "SEEKER":
                sprite, col = "♦", Style.FG_LIME
            elif e["kind"] == "SPINNER":
                sprite, col = "‹❂›", Style.FG_GOLD
            else:
                sprite, col = "╔██╗", Style.FG_RED
            half = len(sprite) // 2
            for idx, ch in enumerate(sprite):
                cx = ix - half + idx
                if 0 <= cx < self.w:
                    grid[iy][cx] = f"{col}{Style.BOLD}{ch}{Style.RESET}"

        for px, py, _, pch, pcol in self.particles:
            ix, iy = int(round(px)), int(round(py))
            if 0 <= ix < self.w and 0 <= iy < self.h:
                grid[iy][ix] = f"{pcol}{Style.BOLD}{pch}{Style.RESET}"

        if not self.game_over and (self.invuln_ticks % 2 == 0 or self.dodge_active > 0):
            ix, iy = int(round(self.px)), int(round(self.py))
            ship = "«◈»" if self.dodge_active > 0 else "◄◈►"
            scol = Style.FG_MAGENTA if self.dodge_active > 0 else Style.FG_CYAN
            for idx, ch in enumerate(ship):
                cx = ix - 1 + idx
                if 0 <= cx < self.w and 0 <= iy < self.h:
                    grid[iy][cx] = f"{scol}{Style.BOLD}{ch}{Style.RESET}"

        for r in range(self.h):
            row_str = "".join(grid[r])
            if self.game_over and r in (self.h // 2 - 1, self.h // 2):
                if r == self.h // 2 - 1:
                    msg = f"{Style.BG_ALERT}{Style.FG_WHITE}{Style.BOLD}  !! OVERRUN IN THE ARENA — SCORE: {self.score:<6} !!  {Style.RESET}"
                else:
                    msg = f"{Style.BG_ALERT}{Style.FG_GOLD}{Style.BOLD}   Press [ENTER/R] to Re-Enter or [Q] Menu   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            elif self.paused and r == self.h // 2:
                msg = f"{Style.BG_SELECT}{Style.FG_WHITE}{Style.BOLD}   || PAUSED - PRESS [P] TO RESUME   {Style.RESET}"
                row_str = pad_center(msg, self.w)
            body.append(pad_center(f"{border_col}│{Style.RESET}{row_str}{border_col}│{Style.RESET}", box_w - 2))

        body.append(pad_center(f"{border_col}└{'─' * self.w}┘{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[WASD/Arrows]{Style.RESET} Move  "
            f"{Style.FG_YELLOW}[SHIFT]{Style.RESET} Blink-Dodge  "
            f"{Style.FG_YELLOW}[B]{Style.RESET} Nova Ring  "
            f"{Style.FG_YELLOW}[F]{Style.RESET} Aim Mode  "
            f"{Style.FG_YELLOW}[Q]{Style.RESET} Menu"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ NEON OVERDRIVE: 360° ARENA SHOOT 'EM UP ★", body, box_w, Style.FG_PINK)

    def run(self):
        self.reset()
        last_step = time.perf_counter()
        while True:
            while True:
                key = self.term.get_key()
                if key is None:
                    break
                if not self.handle_input(key):
                    return

            now = time.perf_counter()
            if now - last_step >= 0.038:
                self.step()
                last_step = now

            self.term.render_frame(self.render())
            time.sleep(0.012)


# ============================================================================
# MAIN ARCADE TUI HUB
# ============================================================================

class ArcadeHub:
    BANNER = [
        "  _____ _____ ____  __  __ ___ _   _    _    _       ",
        " |_   _| ____|  _ \\|  \\/  |_ _| \\ | |  / \\  | |      ",
        "   | | |  _| | |_) | |\\/| || ||  \\| | / _ \\ | |      ",
        "   | | | |___|  _ <| |  | || || |\\  |/ ___ \\| |___   ",
        "   |_| |_____|_| \\_\\_|  |_|___|_| \\_/_/   \\_\\_____|  ",
    ]

    def __init__(self):
        self.term = Terminal()
        self.scores = load_scores()
        self.selected = 0
        self.games = [
            {
                "title": "1. SNAKE ARCADE",
                "color": Style.FG_GREEN,
                "desc": "Classic action Snake with 4 speeds, Portal/Solid walls & Bonus Stars",
                "stat_fn": lambda s: f"High Score: {s['snake_high']} pts",
                "runner": lambda: SnakeGame(self.term, self.scores).run(),
            },
            {
                "title": "2. TIC-TAC-TOE (XO)",
                "color": Style.FG_CYAN,
                "desc": "Play vs Unbeatable Minimax AI, Casual AI, or 2-Player Local XO",
                "stat_fn": lambda s: f"X: {s['xo_x_wins']} | O: {s['xo_o_wins']} | Draws: {s['xo_draws']}",
                "runner": lambda: TicTacToeGame(self.term, self.scores).run(),
            },
            {
                "title": "3. PING PONG ARCADE",
                "color": Style.FG_LIME,
                "desc": "Fast-paced Table Tennis vs 3 AI tiers or 2-Player Local (W/S vs Up/Down)",
                "stat_fn": lambda s: f"P1: {s.get('pong_p1_wins', 0)} | AI/P2: {s.get('pong_p2_wins', 0)} | Rally: {s.get('pong_best_rally', 0)}",
                "runner": lambda: PongGame(self.term, self.scores).run(),
            },
            {
                "title": "4. STARFIGHTER SHMUP",
                "color": Style.FG_BLUE,
                "desc": "Vertical Shoot 'Em Up with [SHIFT] Barrel-Roll Dodge, upgrades & Bosses!",
                "stat_fn": lambda s: f"High Score: {s.get('shmup_high', 0)} pts (Wave {s.get('shmup_max_wave', 1)})",
                "runner": lambda: SpaceShooterGame(self.term, self.scores).run(),
            },
            {
                "title": "5. CYBERWING SHMUP",
                "color": Style.FG_CYAN,
                "desc": "Horizontal R-Type Shoot 'Em Up with Option Drone, Missiles & [SHIFT] Dodge!",
                "stat_fn": lambda s: f"High Score: {s.get('cyberwing_high', 0)} pts",
                "runner": lambda: CyberWingShmupGame(self.term, self.scores).run(),
            },
            {
                "title": "6. NEON ARENA SHMUP",
                "color": Style.FG_PINK,
                "desc": "360° Twin-Stick Bullet-Hell Arena with Auto-Aim & [SHIFT] Blink-Dodge!",
                "stat_fn": lambda s: f"High Score: {s.get('arena_shmup_high', 0)} pts",
                "runner": lambda: NeonArenaShmupGame(self.term, self.scores).run(),
            },
            {
                "title": "7. BRICK BREAKER",
                "color": Style.FG_MAGENTA,
                "desc": "Arkanoid paddle action with Multi-Ball, Wide Paddle & armored bricks",
                "stat_fn": lambda s: f"High Score: {s.get('bricks_high', 0)} pts",
                "runner": lambda: BrickBreakerGame(self.term, self.scores).run(),
            },
            {
                "title": "8. 2048 PUZZLE",
                "color": Style.FG_GOLD,
                "desc": "Slide and merge number tiles to reach the legendary 2048 tile",
                "stat_fn": lambda s: f"Best Tile Score: {s['game_2048_high']} pts",
                "runner": lambda: Game2048(self.term, self.scores).run(),
            },
            {
                "title": "9. CONNECT FOUR",
                "color": Style.FG_RED,
                "desc": "Drop discs & line up 4-in-a-row vs Tactical AI or 2-Player Local",
                "stat_fn": lambda s: f"P1 Wins: {s['c4_p1_wins']} | P2/AI Wins: {s['c4_p2_wins']}",
                "runner": lambda: ConnectFourGame(self.term, self.scores).run(),
            },
        ]

    def render_menu(self) -> list[str]:
        box_w = 84
        body = []
        for line in self.BANNER:
            body.append(pad_center(f"{Style.FG_CYAN}{Style.BOLD}{line}{Style.RESET}", box_w - 2))
        body.append(
            pad_center(
                f"{Style.FG_GOLD}{Style.BOLD}★  CMD / TERMINAL MINI-GAMES ARCADE TUI (9 GAMES)  ★{Style.RESET}",
                box_w - 2,
            )
        )
        body.append(pad_center(f"{Style.FG_GRAY}{'─' * (box_w - 6)}{Style.RESET}", box_w - 2))

        for i, g in enumerate(self.games):
            is_sel = i == self.selected
            prefix = f"{Style.FG_GOLD}► " if is_sel else "  "
            bg = Style.BG_SELECT if is_sel else ""
            title_line = (
                f"{bg}{prefix}{g['color']}{Style.BOLD}{g['title']:<24}{Style.RESET}"
                f"{bg}{Style.FG_WHITE}{g['stat_fn'](self.scores):>44}  {Style.RESET}"
            )
            body.append(pad_center(title_line, box_w - 2))

        sel_game = self.games[self.selected]
        body.append(pad_center(f"{Style.FG_GRAY}{'─' * (box_w - 6)}{Style.RESET}", box_w - 2))
        body.append(
            pad_center(
                f"{Style.BOLD}{sel_game['color']}ABOUT:{Style.RESET} {Style.FG_WHITE}{sel_game['desc']}{Style.RESET}",
                box_w - 2,
            )
        )
        body.append(pad_center(f"{Style.FG_GRAY}{'─' * (box_w - 6)}{Style.RESET}", box_w - 2))
        controls = (
            f"{Style.FG_YELLOW}[▲/▼ or W/S]{Style.RESET} Select   "
            f"{Style.FG_YELLOW}[Enter/Space or 1-9]{Style.RESET} Launch Game   "
            f"{Style.FG_YELLOW}[Q/Esc]{Style.RESET} Exit"
        )
        body.append(pad_center(controls, box_w - 2))

        return draw_box("★ RETRO TERMINAL ARCADE ★", body, box_w, Style.FG_MAGENTA)

    def run(self):
        self.term.enter_tui()
        try:
            while True:
                key = self.term.get_key()
                if key in ("ESC", "Q"):
                    break
                elif key == "UP":
                    self.selected = (self.selected - 1) % len(self.games)
                elif key == "DOWN":
                    self.selected = (self.selected + 1) % len(self.games)
                elif key in ("ENTER", "SPACE"):
                    self.term.clear()
                    self.games[self.selected]["runner"]()
                    self.term.clear()
                elif key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                    idx = int(key) - 1
                    self.selected = idx
                    self.term.clear()
                    self.games[idx]["runner"]()
                    self.term.clear()

                self.term.render_frame(self.render_menu())
                time.sleep(0.03)
        except KeyboardInterrupt:
            pass
        finally:
            self.term.exit_tui()


if __name__ == "__main__":
    # Allow direct CLI shortcut: arcade [snake | xo | pong | shmup | cyberwing | arena | bricks | 2048 | c4 | --install]
    hub = ArcadeHub()
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().lstrip("-")
        if arg in ("h", "help", "?"):
            print("Retro Terminal Arcade TUI (9 Games)")
            print("Usage: arcade [snake | xo | pong | shmup | cyberwing | arena | bricks | 2048 | c4 | --install]")
            sys.exit(0)
        if arg in ("v", "version"):
            print("Retro Terminal Arcade TUI v3.0.0")
            sys.exit(0)
        if arg in ("install", "add-path", "path", "setup"):
            prompt_path_install(hub.scores, force=True)
            sys.exit(0)
        shortcut_map = {
            "snake": 0,
            "xo": 1,
            "tictactoe": 1,
            "tactoc": 1,
            "pong": 2,
            "pingpong": 2,
            "shmup": 3,
            "shooter": 3,
            "space": 3,
            "starfighter": 3,
            "cyberwing": 4,
            "rtype": 4,
            "side": 4,
            "arena": 5,
            "neon": 5,
            "bullethell": 5,
            "bricks": 6,
            "breakout": 6,
            "arkanoid": 6,
            "2048": 7,
            "c4": 8,
            "connect4": 8,
        }
        if arg in shortcut_map:
            prompt_path_install(hub.scores, force=False)
            hub.term.enter_tui()
            try:
                hub.games[shortcut_map[arg]]["runner"]()
            except KeyboardInterrupt:
                pass
            finally:
                hub.term.exit_tui()
            sys.exit(0)
    prompt_path_install(hub.scores, force=False)
    hub.run()
