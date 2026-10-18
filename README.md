# 🕹️ Terminal Arcade TUI

```text
  _____ _____ ____  __  __ ___ _   _    _    _      
 |_   _| ____|  _ \|  \/  |_ _| \ | |  / \  | |     
   | | |  _| | |_) | |\/| || ||  \| | / _ \ | |     
   | | | |___|  _ <| |  | || || |\  |/ ___ \| |___  
   |_| |_____|_| \_\_|  |_|___|_| \_/_/   \_\_____| 
 ★  CMD / TERMINAL MINI-GAMES ARCADE TUI (9 GAMES)  ★
```

**Terminal Arcade** is a zero-dependency, retro-styled **Terminal User Interface (TUI)** mini-games suite built in Python for Windows CMD, PowerShell, Windows Terminal, and Unix terminals. It also ships with a standalone **`arcade.exe`** executable so you can play immediately without installing Python.

---

## ✨ Key Features

- **9 Playable Arcade Classics** in a single unified TUI cabinet.
- **Flicker-Free Rendering**: Uses ANSI alternate screen buffers (`\x1b[?1049h`) and single-write frame flushing for tear-free 60 FPS terminal graphics.
- **Hardware Key Polling**: Uses Win32 `GetAsyncKeyState` for zero-delay continuous movement in action games (Ping Pong, Shoot 'Em Ups, Brick Breaker) and simultaneous 2-player keyboard support.
- **`[SHIFT]` Phase-Dodge Mechanic**: All three Shoot 'Em Up games feature an evasive **`SHIFT` Dodge / Phase-Dash** with invulnerability frames (i-frames), glowing afterimage trails, and **Bullet Graze Bonuses**.
- **Persistent Scoreboard**: Automatically saves high scores, win/draw records, wave records, and best rallies to `arcade_scores.json`.
- **Zero External Dependencies**: Written using only the Python standard library.

---

## 🎮 Included Games (9-in-1)

| # | Game | CLI Shortcut | Genre & Highlights |
| :-: | :--- | :--- | :--- |
| **1** | **Snake Arcade** | `arcade snake` | 4 speed tiers (`CHILL` to `INSANE`), `SOLID` vs wrap-around `PORTAL` walls, and timed Golden Bonus Stars (`★`). |
| **2** | **Tic-Tac-Toe (XO)** | `arcade xo` | Big 3×3 ASCII board with **Unbeatable Minimax AI**, **Casual AI**, and **2P Local** modes. |
| **3** | **Ping Pong Arcade** | `arcade pong` | Fast-paced table tennis vs **3 AI difficulty tiers** or **2P Local** (`W/S` vs `▲/▼`), angled smash shots, and rally tracking. |
| **4** | **Starfighter Shmup** | `arcade shmup` | Vertical-scrolling space Shoot 'Em Up with **`[SHIFT]` Barrel-Roll Dodge**, 3 weapon tiers, shields, Nova Bombs, and Boss Dreadnoughts. |
| **5** | **CyberWing Shmup** | `arcade cyberwing` | Horizontal R-Type / Gradius side-scrolling Shoot 'Em Up with **Orbital Option Drone (`◎`)**, Wave Beams, Missiles, Core Bosses, and **`[SHIFT]` Phase-Boost Dodge**. |
| **6** | **Neon Overdrive Arena** | `arcade arena` | 360° top-down Bullet-Hell Arena Survivor with Auto-Aim / 8-Way Fire, radial Nova Rings, and **`[SHIFT]` Blink-Dodge Shockwave**. |
| **7** | **Brick Breaker** | `arcade bricks` | Classic Arkanoid action with armored bricks and falling `[W]` Wide Paddle, `[M]` Multi-Ball, and `[+]` Extra Ball capsules. |
| **8** | **2048 Puzzle** | `arcade 2048` | Color-coded 4×4 sliding tile puzzle with **Undo (`U`)** support and high-score tracking. |
| **9** | **Connect Four** | `arcade c4` | 6×7 disc-drop strategy board with **1P vs Tactical AI** and **2P Local** modes. |

---

## 🚀 Quick Start

### Option 1: Run the Standalone Executable (Windows)
No Python installation required. Double-click **`arcade.exe`** in File Explorer, or run it from `cmd.exe` / PowerShell:

```cmd
.\arcade.exe
```

### Option 2: Run with Python
Requires Python 3.10+:

```cmd
python arcade.py
```
*(Or simply run `arcade.bat` from CMD).*

### Direct Game Launch Shortcuts
Jump straight into any game from the command line:

```cmd
arcade snake       :: 1. Snake Arcade
arcade xo          :: 2. Tic-Tac-Toe (XO)
arcade pong        :: 3. Ping Pong Arcade
arcade shmup       :: 4. Starfighter (Vertical Shoot 'Em Up)
arcade cyberwing   :: 5. CyberWing (Horizontal R-Type Shoot 'Em Up)
arcade arena       :: 6. Neon Overdrive (360° Bullet-Hell Arena)
arcade bricks      :: 7. Brick Breaker (Arkanoid)
arcade 2048        :: 8. 2048 Puzzle
arcade c4          :: 9. Connect Four
```

---

## ⌨️ Controls Reference

### Main Menu
- **`▲ / ▼`** or **`W / S`**: Navigate game list
- **`Enter / Space`** or **`1 – 9`**: Launch selected game
- **`Q` / `Esc`**: Exit to terminal

### Action Games (Shoot 'Em Ups, Ping Pong, Snake, Brick Breaker)
- **`WASD`** or **`Arrow Keys`**: Move ship / paddle / snake
- **`SHIFT`** *(or `C`)*: **Phase-Dodge / Barrel-Roll / Blink-Dash** *(in all 3 Shoot 'Em Ups)*
- **`Space`** *(or `Z`)*: Fire weapons / Pause
- **`B`** *(or `X`)*: Trigger **Nova Bomb / EMP Ring** *(in Shoot 'Em Ups)*
- **`F`**: Toggle Auto-Fire / Auto-Aim mode *(in Shoot 'Em Ups)*
- **`M` / `Tab`**: Cycle difficulty speed, AI tier, or wall mode
- **`P`**: Pause / Resume game
- **`R`**: Restart current game
- **`Q` / `Esc`**: Return to Main Menu

### Board & Puzzle Games (Tic-Tac-Toe, 2048, Connect Four)
- **`WASD`** or **`Arrow Keys`**: Move cursor / slide tiles
- **`1 – 9`**: Quick cell or column selection *(Tic-Tac-Toe & Connect Four)*
- **`Space` / `Enter`**: Place mark / drop disc
- **`U`**: Undo last move *(2048)*
- **`M` / `Tab`**: Switch between 1P AI and 2P Local modes
- **`R`**: Reset board / swap starting player

---

## 🛠️ Building `arcade.exe` from Source

To package `arcade.py` into a standalone single-file Windows executable using [PyInstaller](https://pyinstaller.org/):

```cmd
pip install pyinstaller
python -m PyInstaller --onefile --console --clean --name arcade --distpath . arcade.py
```

---

## 📄 License

Open-source and free to play, modify, and share.
