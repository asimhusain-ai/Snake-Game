# 🐍 Snake Game

**Developed by:** Asim Husain – Intermediate Python Developer  
**Date:** September 29, 2025  
**Version:** 1.0

---

## 🔹 Description

**Advanced Snake Game** is a modern take on the classic Snake game, developed using **Python** and **Pygame**. It includes multiple game modes, custom obstacles, particle effects, sound effects, and a high-score leaderboard. The game is optimized to run smoothly on Windows as a standalone executable without requiring Python to be installed.

**Key Features:**
- Multiple game modes: Classic, Wall-less, Speed-up, Obstacle, Multi-fruit
- Dynamic fruit types with special effects (gold apple, grape, etc.)
- Particle effects and smooth animations
- High-score leaderboard with player names
- Customizable difficulty: Easy, Medium, Hard
- Background music and sound effects
- Fully portable EXE build with embedded assets
- Modern UI with custom fonts and input handling

---

## 🔹 Tools & Technologies Used

- **Programming Language:** Python 3.12  
- **Game Engine:** Pygame 2.6  
- **Asset Management:** Fonts & sounds stored in `assets` folder  
- **Packaging:** PyInstaller for creating standalone EXE  
- **IDE:** Visual Studio Code (or any Python IDE)

**Assets:**
- Fonts: `Ubuntu-Bold.ttf`, `Ubuntu-Regular.ttf`  
- Sounds: `background_music.ogg`, `eat_fruit.wav`, `game_over.wav`, `click.wav`

---

## 📂 Project Structure

```text
Snake/
├── assets/
│   ├── fonts/
│   │   ├── Ubuntu-Bold.ttf
│   │   └── Ubuntu-Regular.ttf
│   └── sounds/
│       ├── background_music.ogg
│       ├── click.wav
│       ├── eat_fruit.wav
│       └── game_over.wav
├── snake.py
├── icon.ico
├── SnakeGame.exe
└── README.md


---

## 🔹 Development Notes
- This project took 15+ hours to develop.
- Includes advanced gameplay mechanics and UI polish.
- Uses Python object-oriented programming for Snake, Fruit, and Obstacle classes.
- Sound and particle effects enhance game feel.
- Designed with modularity in mind: you can easily add new fruit types, obstacles, or game modes.
- High-score system stored in high_scores.json for persistence (consider moving to %APPDATA%/SnakeGame/ for installed users).

---

## 🔹 Future Improvements
- Add network multiplayer mode
- Include more complex levels and obstacles
- Add settings UI for music/sound volume and controls
- Implement more visual effects, themes and accessibility options
- Create automated builds and CI (GitHub Actions) to produce EXE releases

---

## 🔹 Author
- Made With ❤️ Asim Husain [ www.asimhusain.dev ]

---

## 🔹 Installation & Running

### 1. **Requirements (For Development)**
- Python 3.12 installed
- Pygame 2.6 (`pip install pygame`)
- Optional: VS Code or PyCharm 

### 2. **Run From Source**
```bash
git clone <your-repo-url>
cd Snake
pip install pygame
python snake.py
