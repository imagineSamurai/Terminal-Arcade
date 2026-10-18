<div align="center">

```text
  _____ _____ ____  __  __ ___ _   _    _    _      
 |_   _| ____|  _ \|  \/  |_ _| \ | |  / \  | |     
   | | |  _| | |_) | |\/| || ||  \| | / _ \ | |     
   | | | |___|  _ <| |  | || || |\  |/ ___ \| |___  
   |_| |_____|_| \_\_|  |_|___|_| \_/_/   \_\_____| 
 ★  CMD / TERMINAL MINI-GAMES ARCADE TUI (9 GAMES)  ★
```

# Terminal Arcade

*Retro 9-in-1 mini-games cabinet for Windows CMD, PowerShell, and Terminal*

[![Python](https://img.shields.io/badge/Python->=3.10-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078d4?style=flat-square)](https://github.com/imagineSamurai/Terminal-Arcade)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero-2ea44f?style=flat-square)](https://github.com/imagineSamurai/Terminal-Arcade)
[![Games](https://img.shields.io/badge/Games-9%20Included-f39c12?style=flat-square)](#games)

⭐ If you like this project, star it on GitHub!

[Features](#features) • [Games](#games) • [Quick Start](#quick-start) • [Controls](#controls) • [Building from Source](#building-from-source)

</div>

**Terminal Arcade** is a zero-dependency, retro-styled Terminal User Interface (TUI) gaming suite written in pure Python. It runs natively inside `cmd.exe`, PowerShell, Windows Terminal, and Unix shells, and includes a standalone **`arcade.exe`** executable so you can play immediately on Windows without installing Python.

## Features

- **9 Playable Arcade Classics** — Action, shoot 'em up, sports, puzzle, and strategy games in one unified cabinet.
- **Flicker-Free 60 FPS Rendering** — Uses ANSI alternate screen buffers (`\x1b[?1049h`) and synchronized single-write frame flushing with zero screen tearing.
- **Hardware Key-State Polling** — Uses Win32 `GetAsyncKeyState` for responsive continuous movement in action games and simultaneous 2-player local keyboard input.
- **`[SHIFT]` Phase-Dodge System** — All three Shoot 'Em Up titles feature an evasive **`SHIFT` Dash / Dodge** with invulnerability frames (i-frames), glowing afterimage trails, and **Bullet Graze (`+25`)** proximity bonuses.
- **Persistent High Scores** — Automatically tracks and saves high scores, win/draw records, highest waves, and longest rallies in `arcade_scores.json`.
- **Zero External Dependencies** — Built entirely with the Python standard library.

## Games

| # | Game | CLI Command | Overview |
| :-: | :--- | :--- | :--- |
| **1** | **Snake Arcade** | `arcade snake` | 4 speed tiers (`CHILL` to `INSANE`), `SOLID` vs wrap-around `PORTAL` walls, and timed Golden Bonus Stars (`★`). |
| **2** | **Tic-Tac-Toe (XO)** | `arcade xo` | Full-sized 3×3 ASCII board with **Unbeatable Minimax AI**, **Casual AI**, and **2P Local** modes. |
| **3** | **Ping Pong Arcade** | `arcade pong` | Fast-paced table tennis with **3 AI difficulty tiers** or **2P Local** (`W/S` vs `▲/▼`), angled smash shots, and rally tracking. |
| **4** | **Starfighter Shmup** | `arcade shmup` | Vertical space Shoot 'Em Up with **`[SHIFT]` Barrel-Roll Dodge**, 3 weapon tiers, shields, Nova Bombs, and Boss Dreadnoughts. |
| **5** | **CyberWing Shmup** | `arcade cyberwing` | Horizontal R-Type / Gradius side-scroller with **Orbital Option Drone (`◎`)**, Wave Beams, Homing Missiles, Core Bosses, and **`[SHIFT]` Phase-Boost Dodge**. |
| **6** | **Neon Overdrive Arena** | `arcade arena` | 360° top-down Bullet-Hell Arena Survivor with Auto-Aim / 8-Way Fire, radial EMP Nova Rings, and **`[SHIFT]` Blink-Dodge Shockwave**. |
| **7** | **Brick Breaker** | `arcade bricks` | Classic Arkanoid action with multi-hit armored bricks and falling `[W]` Wide Paddle, `[M]` Multi-Ball, and `[+]` Extra Ball capsules. |
| **8** | **2048 Puzzle** | `arcade 2048` | Color-coded 4×4 sliding tile puzzle with **Undo (`U`)** support and milestone tracking past `2048`. |
| **9** | **Connect Four** | `arcade c4` | 6×7 disc-drop strategy board with **1P vs Tactical AI** (center-control & threat blocking) and **2P Local** modes. |

## Quick Start

### Standalone Executable (Windows)

No Python installation is required. Double-click **`arcade.exe`** in File Explorer or launch it from `cmd.exe` / PowerShell:

```cmd
.\arcade.exe
```

### Python Script

Requires Python 3.10 or newer:

```bash
python arcade.py
```

> [!TIP]
> On Windows CMD, you can also use the included `arcade.bat` wrapper to launch the menu or pass a game shortcut directly (e.g., `arcade shmup`).

### Direct CLI Shortcuts

Pass a game name as an argument to bypass the main menu and jump straight into a game:

```bash
arcade snake       # 1. Snake Arcade
arcade xo          # 2. Tic-Tac-Toe (XO)
arcade pong        # 3. Ping Pong Arcade
arcade shmup       # 4. Starfighter (Vertical Shoot 'Em Up)
arcade cyberwing   # 5. CyberWing (Horizontal R-Type Shoot 'Em Up)
arcade arena       # 6. Neon Overdrive (360° Bullet-Hell Arena)
arcade bricks      # 7. Brick Breaker (Arkanoid)
arcade 2048        # 8. 2048 Puzzle
arcade c4          # 9. Connect Four
```

## Controls

### Main Menu

| Key | Action |
| :--- | :--- |
| `▲ / ▼` or `W / S` | Navigate game selection |
| `Enter` / `Space` / `1–9` | Launch selected game |
| `X` | Reset saved high scores |
| `Q` / `Esc` | Exit to terminal |

### Action & Shoot 'Em Up Games

| Key | Action |
| :--- | :--- |
| `WASD` or `Arrow Keys` | Move ship, paddle, or snake (`2P Pong`: `W/S` for Left, `▲/▼` for Right) |
| `SHIFT` *(or `C`)* | **Phase-Dodge / Barrel-Roll / Blink-Dash** *(invulnerability frames in all 3 Shoot 'Em Ups)* |
| `Space` *(or `Z`)* | Fire primary weapons / Launch ball |
| `B` *(or `X`)* | Trigger **Nova Bomb / EMP Ring** *(clears enemy bullets & damages bosses)* |
| `F` | Toggle Auto-Fire / Auto-Aim mode *(Shoot 'Em Ups)* |
| `M` / `Tab` | Cycle speed tier, AI difficulty, or wall mode |
| `P` | Pause / Resume game |
| `R` | Restart current game |
| `Q` / `Esc` | Return to Main Menu |

> [!NOTE]
> Dashing through enemy projectiles with `SHIFT` while invulnerable awards a **Graze Bonus (`+25` pts per bullet)** and leaves an afterimage trail. In **Neon Overdrive Arena**, ending a dash also triggers a local EMP shockwave that vaporizes nearby enemy fire.

### Board & Puzzle Games

| Key | Action |
| :--- | :--- |
| `WASD` or `Arrow Keys` | Move board cursor / Slide 2048 tiles |
| `1–9` | Direct cell selection *(Tic-Tac-Toe)* or column drop *(Connect Four)* |
| `Space` / `Enter` | Place mark / Drop disc |
| `U` | Undo last move *(2048)* |
| `M` / `Tab` | Toggle between **1P vs AI** and **2P Local** modes |
| `R` | Reset board / Swap starting player |
| `Q` / `Esc` | Return to Main Menu |

## Building from Source

To package `arcade.py` into a standalone single-file Windows executable (`arcade.exe`) using [PyInstaller](https://pyinstaller.org/):

```cmd
pip install pyinstaller
python -m PyInstaller --onefile --console --clean --name arcade --distpath . arcade.py
```
