# Advanced Snake Game
# Developed by Asim Husain - An Intermediate Python Developer
# September 29, 2025

import pygame
import sys
import random
import json
from datetime import datetime
import math
import os

# --- Resource Helper Function ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Initialization ---
pygame.init()
pygame.mixer.init()

# --- Game Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720 
GRID_SIZE = 30
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE

# Colors
COLOR_BG = (15, 20, 30)
COLOR_GRID = (25, 30, 40)
COLOR_SNAKE_HEAD = (115, 210, 220)
COLOR_SNAKE_BODY = (80, 160, 170)
COLOR_OBSTACLE = (120, 120, 120)
COLOR_TEXT = (220, 220, 220)
COLOR_ACCENT = (230, 100, 100)
COLOR_GOLD = (255, 215, 0)
COLOR_PURPLE = (180, 120, 255)
COLOR_INPUT_BOX = (40, 50, 65)

# Game settings
FPS = 60

# --- Load Fonts ---
try:
    FONT_PATH_REGULAR = resource_path('assets/fonts/Ubuntu-Regular.ttf')
    FONT_PATH_BOLD = resource_path('assets/fonts/Ubuntu-Bold.ttf')
    FONT_S = pygame.font.Font(FONT_PATH_REGULAR, 18)
    FONT_M = pygame.font.Font(FONT_PATH_REGULAR, 24)
    FONT_L = pygame.font.Font(FONT_PATH_BOLD, 48)
    FONT_XL = pygame.font.Font(FONT_PATH_BOLD, 72)
except FileNotFoundError:
    print("Warning: Font files not found. Using default font.")
    FONT_S = pygame.font.SysFont('sans-serif', 18)
    FONT_M = pygame.font.SysFont('sans-serif', 24)
    FONT_L = pygame.font.SysFont('sans-serif', 48, bold=True)
    FONT_XL = pygame.font.SysFont('sans-serif', 72, bold=True)

# --- Load Sounds ---
try:
    SOUND_EAT = pygame.mixer.Sound(resource_path('assets/sounds/eat_fruit.wav'))
    SOUND_GAMEOVER = pygame.mixer.Sound(resource_path('assets/sounds/game_over.wav'))
    SOUND_CLICK = pygame.mixer.Sound(resource_path('assets/sounds/click.wav'))
    SOUND_EAT.set_volume(0.3)
    SOUND_GAMEOVER.set_volume(0.2)
    SOUND_CLICK.set_volume(0.3)
    pygame.mixer.music.load(resource_path('assets/sounds/background_music.ogg'))
    pygame.mixer.music.set_volume(0.05)
except pygame.error as e:
    print(f"Warning: Sound file not found or failed to load: {e}")
    class DummySound:
        def play(self): pass
        def set_volume(self, vol): pass
    SOUND_EAT = SOUND_GAMEOVER = SOUND_CLICK = DummySound()

    class DummyMusic:
        def load(self, file): pass
        def play(self, loops): pass
        def stop(self): pass
        def set_volume(self, vol): pass
    pygame.mixer.music = DummyMusic()

# --- Helper Functions & Classes ---
def draw_text(text, font, color, surface, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.radius = random.randint(4, 8)
        self.life = 20
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius -= 0.2
        self.life -= 1
        return self.radius > 0

    def draw(self, surface):
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

# --- Game Object Classes ---
class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        self.length = 1
        self.positions = [((GRID_WIDTH // 2), (GRID_HEIGHT // 2))]
        self.direction = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
        self.color_head = COLOR_SNAKE_HEAD
        self.color_body = COLOR_SNAKE_BODY
        self.body_palette = [(80, 160, 170), (90, 180, 190), (70, 140, 150), (100, 200, 210)]
        self.next_direction = self.direction

    def get_head_position(self):
        return self.positions[0]

    def turn(self, point):
        if self.length > 1 and (point[0] * -1, point[1] * -1) == self.direction:
            return
        self.next_direction = point

    def move(self, wall_less_mode):
        self.direction = self.next_direction
        cur = self.get_head_position()
        x, y = self.direction
        new = ((cur[0] + x), (cur[1] + y))
        if wall_less_mode:
            new = (new[0] % GRID_WIDTH, new[1] % GRID_HEIGHT)
        self.positions.insert(0, new)
        if len(self.positions) > self.length:
            self.positions.pop()

    def grow(self):
        self.length += 1

    def collides_with_self(self):
        return self.get_head_position() in self.positions[1:]

    def collides_with_wall(self):
        x, y = self.get_head_position()
        return x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT

    def collides_with_obstacles(self, obstacles):
        return self.get_head_position() in [obs.pos for obs in obstacles]

    def draw(self, surface):
        for i, p in enumerate(self.positions[1:]):
            r = pygame.Rect((p[0] * GRID_SIZE, p[1] * GRID_SIZE), (GRID_SIZE, GRID_SIZE))
            color = self.body_palette[i % len(self.body_palette)]
            pygame.draw.rect(surface, color, r)
            pygame.draw.rect(surface, COLOR_GRID, r, 1)
        head_rect = pygame.Rect((self.positions[0][0] * GRID_SIZE, self.positions[0][1] * GRID_SIZE), (GRID_SIZE, GRID_SIZE))
        pygame.draw.rect(surface, self.color_head, head_rect)
        pygame.draw.rect(surface, COLOR_GRID, head_rect, 2)


class Fruit:
    """Manages fruit properties and drawing."""
    FRUIT_TYPES = {
        'apple': {'color': COLOR_ACCENT, 'score': 10, 'effect': None},
        'gold_apple': {'color': COLOR_GOLD, 'score': 50, 'effect': 'speed_boost'},
        'grape': {'color': COLOR_PURPLE, 'score': 20, 'effect': 'slow_down'}
    }

    def __init__(self, fruit_type='apple'):
        self.type = fruit_type
        self.properties = self.FRUIT_TYPES[fruit_type]
        self.pos = (0, 0)
        self.spawn_animation_timer = 30

    def randomize_position(self, snake_positions, obstacle_positions):
        while True:
            new_pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if new_pos not in snake_positions and new_pos not in obstacle_positions:
                self.pos = new_pos
                self.spawn_animation_timer = 30
                break

    def draw(self, surface):
        r = pygame.Rect((self.pos[0] * GRID_SIZE, self.pos[1] * GRID_SIZE), (GRID_SIZE, GRID_SIZE))
        if self.spawn_animation_timer > 0:
            scale = 1.0 - (self.spawn_animation_timer / 30.0)
            anim_rect = r.inflate(GRID_SIZE * (scale-1), GRID_SIZE * (scale-1))
            pygame.draw.rect(surface, self.properties['color'], anim_rect, border_radius=8)
            self.spawn_animation_timer -= 1
        else:
            pygame.draw.rect(surface, self.properties['color'], r, border_radius=8)


class Obstacle:
    """Manages obstacle positions and drawing."""
    def __init__(self, pos):
        self.pos = pos

    def draw(self, surface):
        r = pygame.Rect((self.pos[0] * GRID_SIZE, self.pos[1] * GRID_SIZE), (GRID_SIZE, GRID_SIZE))
        pygame.draw.rect(surface, COLOR_OBSTACLE, r)
        pygame.draw.rect(surface, COLOR_GRID, r, 2)


# --- Main Game Class ---
class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(" S N A K E ")
        self.clock = pygame.time.Clock()
        self.game_state = "MAIN_MENU"
        self.particles = []

        # Game settings
        self.game_mode = "Classic"
        self.difficulty = "Medium"
        self.player_name = ""

        # Game objects
        self.snake = Snake()
        self.fruits = []
        self.obstacles = []
        self.reset_game_state()

        # UI elements for menus
        self.menu_buttons = {
            "game_mode": ["Classic", "Wall-less", "Speed-up", "Obstacle", "Multi-fruit"],
            "difficulty": ["Easy", "Medium", "Hard"],
            "start": ["Start Game"],
            "leaderboard": ["Leaderboard"],
            "quit": ["Quit"]
        }
        self.selected_button = ("game_mode", 0)
        self.high_scores = self.load_scores()
        
        # Score animation
        self.score_anim_timer = 0


    def reset_game_state(self):
        """Resets all variables for a new game."""
        self.snake.reset()
        self.score = 0
        self.game_over_flag = False
        self.obstacles.clear()
        self.fruits.clear()

        # Set speed based on difficulty
        self.base_speed = {'Easy': 8, 'Medium': 12, 'Hard': 16}[self.difficulty]
        self.current_speed = self.base_speed
        self.move_timer = 0

        # Generate obstacles if in Obstacle mode
        if self.game_mode == "Obstacle":
            num_obstacles = {'Easy': 10, 'Medium': 20, 'Hard': 30}[self.difficulty]
            for _ in range(num_obstacles):
                pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
                if pos not in self.snake.positions:
                    self.obstacles.append(Obstacle(pos))
        
        # Spawn initial fruit
        self.spawn_fruit()

    def spawn_fruit(self):
        """Spawns fruit(s) based on the game mode."""
        self.fruits.clear()
        num_fruits = 3 if self.game_mode == 'Multi-fruit' else 1
        
        for _ in range(num_fruits):
            if self.game_mode == 'Multi-fruit':
                fruit_choice = random.choices(['apple', 'gold_apple', 'grape'], weights=[70, 10, 20], k=1)[0]
                fruit = Fruit(fruit_choice)
            else:
                fruit = Fruit('apple')
            
            occupied_pos = self.snake.positions + [obs.pos for obs in self.obstacles] + [f.pos for f in self.fruits]
            fruit.randomize_position(self.snake.positions, [obs.pos for obs in self.obstacles])
            self.fruits.append(fruit)

    def load_scores(self):
        """Loads scores from a JSON file."""
        try:
            with open('high_scores.json', 'r') as f:
                scores = json.load(f)
                return sorted(scores, key=lambda x: x['score'], reverse=True)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_score(self):
        """Saves the current score if it's a high score."""
        if not self.player_name: self.player_name = "Anonymous"
        
        score_entry = {
            "name": self.player_name,
            "score": self.score,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "mode": self.game_mode,
            "difficulty": self.difficulty
        }
        self.high_scores.append(score_entry)
        self.high_scores = sorted(self.high_scores, key=lambda x: x['score'], reverse=True)[:10] # Keep top 10
        with open('high_scores.json', 'w') as f:
            json.dump(self.high_scores, f, indent=4)

    def create_particle_burst(self, position, color):
        """Creates a burst of particles at a given position."""
        x, y = (position[0] * GRID_SIZE + GRID_SIZE // 2, position[1] * GRID_SIZE + GRID_SIZE // 2)
        for _ in range(20):
            self.particles.append(Particle(x, y, color))

    def update_particles(self):
        """Updates and removes dead particles."""
        self.particles = [p for p in self.particles if p.update()]

    def draw_background(self):
        """Draws the background and grid."""
        self.screen.fill(COLOR_BG)

        for x in range(0, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (SCREEN_WIDTH, y))
            
    def draw_hud(self):
        score_text = f"Score: {self.score}"
        if self.score_anim_timer > 0:
            scale = 1 + 0.5 * (self.score_anim_timer / 15)
            font = pygame.font.Font(FONT_PATH_BOLD, int(28 * scale))
            self.score_anim_timer -= 1
        else:
            font = pygame.font.Font(FONT_PATH_BOLD, 28)
        
        draw_text(score_text, font, COLOR_TEXT, self.screen, 20, 20)
        draw_text(f"Mode: {self.game_mode}", FONT_M, COLOR_TEXT, self.screen, 20, 60)
        draw_text(f"Difficulty: {self.difficulty}", FONT_M, COLOR_TEXT, self.screen, 20, 90)

    def handle_game_events(self):
        """Handles user input during the game."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_UP, pygame.K_w]:
                    self.snake.turn((0, -1))
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.snake.turn((0, 1))
                elif event.key in [pygame.K_LEFT, pygame.K_a]:
                    self.snake.turn((-1, 0))
                elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                    self.snake.turn((1, 0))
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = "Main Menu"
                    pygame.mixer.music.play(-1)

    def update_game_logic(self):
        """Updates the game state each frame."""
        if self.game_over_flag:
            return

        self.move_timer += self.clock.get_time()
        move_interval = 1000 / self.current_speed
        if self.move_timer >= move_interval:
            self.move_timer = 0
            self.snake.move(self.game_mode == "Wall-less")

            head_pos = self.snake.get_head_position()
            
            # Collision with fruit
            for fruit in self.fruits[:]: 
                if head_pos == fruit.pos:
                    self.score += fruit.properties['score']
                    self.snake.grow()
                    SOUND_EAT.play()
                    self.create_particle_burst(fruit.pos, fruit.properties['color'])
                    self.score_anim_timer = 15 

                    # Handle fruit effects
                    if fruit.properties['effect'] == 'speed_boost':
                        self.current_speed *= 1.5
                    elif fruit.properties['effect'] == 'slow_down':
                        self.current_speed = max(self.base_speed, self.current_speed * 0.75)

                    self.fruits.remove(fruit)
                    if not self.fruits:
                        self.spawn_fruit()

            # Collision with self
            if self.snake.collides_with_self():
                self.game_over()

            # Collision with wall
            if self.game_mode != "Wall-less" and self.snake.collides_with_wall():
                self.game_over()
            
            # Collision with obstacles
            if self.game_mode == "Obstacle" and self.snake.collides_with_obstacles(self.obstacles):
                self.game_over()

            # Speed-up mode logic
            if self.game_mode == "Speed-up":
                self.current_speed += 0.05
    
    def game_over(self):
        """Handles the game over sequence."""
        self.game_over_flag = True
        SOUND_GAMEOVER.play()
        pygame.mixer.music.stop()
        self.game_state = "GAME_OVER"
        self.player_name = ""
        self.high_scores = self.load_scores()

    def draw_game_elements(self):
        """Draws all active game objects."""
        for obs in self.obstacles:
            obs.draw(self.screen)
        for fruit in self.fruits:
            fruit.draw(self.screen)
        self.snake.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)
    
    def game_over_transition(self, progress):
        """Draws a fade-to-black transition effect."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(int(255 * progress))
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
    def main_loop(self):
        """The main loop for the entire application."""
        while True:
            if self.game_state == "MAIN_MENU":
                self.main_menu_screen()
            elif self.game_state == "PLAYING":
                self.game_play_screen()
            elif self.game_state == "GAME_OVER":
                self.game_over_screen()
            elif self.game_state == "LEADERBOARD":
                self.leaderboard_screen()

            pygame.display.flip()
            self.clock.tick(FPS)


    def main_menu_screen(self):
        """Displays the main menu and handles its logic."""
        self.draw_background()
        draw_text("S N A K E - G A M E", FONT_XL, COLOR_ACCENT, self.screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4, center=True)
        
        button_rects = {}

        # Render menu options
        y_pos = SCREEN_HEIGHT / 2 - 50
        button_keys = list(self.menu_buttons.keys())
        for i, (key, options) in enumerate(self.menu_buttons.items()):
            label = key.replace("_", " ").title()
            
            if key in ["game_mode", "difficulty"]:
                current_selection_index = self.menu_buttons[key].index(getattr(self, key))
                value = self.menu_buttons[key][current_selection_index]
                display_text = f"{label}: {value}"
            else:
                display_text = label

            is_selected = self.selected_button[0] == key
            color = COLOR_ACCENT if is_selected else COLOR_TEXT
            
            text_surf = FONT_L.render(display_text, True, color)
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH / 2, y_pos))
            self.screen.blit(text_surf, text_rect)
            
            button_rects[key] = text_rect
            y_pos += 70

        # Handle menu input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for key, rect in button_rects.items():
                        if rect.collidepoint(event.pos):
                            SOUND_CLICK.play()
                            self.selected_button = (key, 0)
                            
                            # --- Action on click ---
                            if key == "start":
                                self.reset_game_state()
                                self.game_state = "PLAYING"
                                pygame.mixer.music.stop()
                            elif key == "leaderboard":
                                self.game_state = "LEADERBOARD"
                            elif key == "quit":
                                pygame.quit(), sys.exit()

            # --- KEYBOARD LOGIC ---
            if event.type == pygame.KEYDOWN:
                SOUND_CLICK.play()
                current_cat, current_idx = self.selected_button
                current_cat_idx = button_keys.index(current_cat)
                
                if event.key in [pygame.K_UP, pygame.K_w]:
                    new_cat_idx = (current_cat_idx - 1) % len(button_keys)
                    self.selected_button = (button_keys[new_cat_idx], 0)
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    new_cat_idx = (current_cat_idx + 1) % len(button_keys)
                    self.selected_button = (button_keys[new_cat_idx], 0)
                elif event.key in [pygame.K_LEFT, pygame.K_a]:
                    if current_cat in ["game_mode", "difficulty"]:
                        options = self.menu_buttons[current_cat]
                        current_val_idx = options.index(getattr(self, current_cat))
                        new_val_idx = (current_val_idx - 1) % len(options)
                        setattr(self, current_cat, options[new_val_idx])
                elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                    if current_cat in ["game_mode", "difficulty"]:
                        options = self.menu_buttons[current_cat]
                        current_val_idx = options.index(getattr(self, current_cat))
                        new_val_idx = (current_val_idx + 1) % len(options)
                        setattr(self, current_cat, options[new_val_idx])
                elif event.key == pygame.K_RETURN:
                    if current_cat == "start":
                        self.reset_game_state()
                        self.game_state = "PLAYING"
                        pygame.mixer.music.stop()
                    elif current_cat == "leaderboard":
                        self.game_state = "LEADERBOARD"
                    elif current_cat == "quit":
                        pygame.quit(), sys.exit()

    def game_play_screen(self):
        """Manages the active gameplay session."""
        self.handle_game_events()
        self.update_game_logic()
        
        self.draw_background()
        self.draw_game_elements()
        self.draw_hud()
        self.update_particles()

    def game_over_screen(self):
        """Displays the game over screen and input for name."""
        self.draw_background()
        self.draw_game_elements()

        # Game Over text
        draw_text("GAME OVER", FONT_XL, COLOR_ACCENT, self.screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4, center=True)
        draw_text(f"Final Score: {self.score}", FONT_L, COLOR_TEXT, self.screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50, center=True)
        
        input_rect = pygame.Rect(0, 0, 300, 50)
        input_rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50)

        draw_text("Enter Name:", FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH / 2, input_rect.top - 30, center=True)

        pygame.draw.rect(self.screen, COLOR_INPUT_BOX, input_rect)
        pygame.draw.rect(self.screen, COLOR_TEXT, input_rect, 2)  
        draw_text(self.player_name, FONT_M, COLOR_TEXT, self.screen, input_rect.x + 10, input_rect.y + 10)
        draw_text("Enter Name , Press Enter", FONT_S, COLOR_TEXT, self.screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.75, center=True)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.save_score()
                    self.game_state = "LEADERBOARD"
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = "MAIN_MENU"
                    pygame.mixer.music.play(-1)
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                elif len(self.player_name) < 20: 
                    self.player_name += event.unicode
                    
    def leaderboard_screen(self):
        """Displays the high scores."""
        self.draw_background()
        draw_text("Leaderboard", FONT_XL, COLOR_GOLD, self.screen, SCREEN_WIDTH / 2, 100, center=True)

        y_pos = 200

        draw_text("Rank", FONT_M, COLOR_ACCENT, self.screen, SCREEN_WIDTH * 0.2, y_pos)
        draw_text("Name", FONT_M, COLOR_ACCENT, self.screen, SCREEN_WIDTH * 0.3, y_pos)
        draw_text("Score", FONT_M, COLOR_ACCENT, self.screen, SCREEN_WIDTH * 0.5, y_pos)
        draw_text("Mode", FONT_M, COLOR_ACCENT, self.screen, SCREEN_WIDTH * 0.6, y_pos)
        draw_text("Difficulty", FONT_M, COLOR_ACCENT, self.screen, SCREEN_WIDTH * 0.8, y_pos)
        y_pos += 40

        for i, entry in enumerate(self.high_scores):
            rank = f"#{i+1}"
            draw_text(rank, FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH * 0.2, y_pos)
            draw_text(entry['name'], FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH * 0.3, y_pos)
            draw_text(str(entry['score']), FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH * 0.5, y_pos)
            draw_text(entry['mode'], FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH * 0.6, y_pos)
            draw_text(entry['difficulty'], FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH * 0.8, y_pos)
            y_pos += 40
        
        draw_text("Press ESC to return to Main Menu", FONT_M, COLOR_TEXT, self.screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50, center=True)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(), sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_state = "MAIN_MENU"
                pygame.mixer.music.play(-1)


if __name__ == '__main__':
    game = SnakeGame()
    pygame.mixer.music.play(-1)
    game.main_loop()