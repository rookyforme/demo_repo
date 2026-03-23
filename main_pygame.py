#!/usr/bin/env python3
import random
import sys

import pygame


COLS = 10
ROWS = 20
CELL = 24

PANEL_W = 200
FPS = 60

TYPES = ["I", "J", "L", "O", "S", "T", "Z"]
TYPE_TO_IDX = {t: i + 1 for i, t in enumerate(TYPES)}  # board stores 0 or 1..7

COLORS = {
    TYPE_TO_IDX["I"]: (0, 229, 255),
    TYPE_TO_IDX["J"]: (63, 81, 181),
    TYPE_TO_IDX["L"]: (255, 152, 0),
    TYPE_TO_IDX["O"]: (255, 235, 59),
    TYPE_TO_IDX["S"]: (76, 175, 80),
    TYPE_TO_IDX["T"]: (156, 39, 176),
    TYPE_TO_IDX["Z"]: (244, 67, 54),
}

GRID_BG = (15, 15, 18)
GRID_LINE = (28, 28, 34)
TEXT_FG = (234, 234, 240)


def rotate_coords_4x4(coords):
    # Rotate 4x4 coordinates (x, y) -> (y, 3-x)
    return [(y, 3 - x) for (x, y) in coords]


def build_rotations(initial_coords):
    rotations = []
    coords = list(initial_coords)
    for _ in range(4):
        rotations.append(coords)
        coords = rotate_coords_4x4(coords)
    return rotations


SHAPES_4X4 = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
}

ROTATIONS = {t: build_rotations(SHAPES_4X4[t]) for t in TYPES}


class TetrisGame:
    def __init__(self):
        self.score = 0
        self.level = 0
        self.lines = 0

        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = []

        self.curr_type = None
        self.next_type = None
        self.px = 3
        self.py = -1
        self.rot = 0

        self.game_over = False
        self.paused = False

        self.drop_interval_ms = 800
        self.last_drop_ms = 0

    def make_shuffled_bag(self):
        bag = TYPES[:]
        random.shuffle(bag)
        return bag

    def get_next_type(self):
        if not self.bag:
            self.bag = self.make_shuffled_bag()
        return self.bag.pop()

    def reset(self):
        self.score = 0
        self.level = 0
        self.lines = 0

        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = []

        self.game_over = False
        self.paused = False
        self.drop_interval_ms = 800

        self.next_type = self.get_next_type()
        self.spawn_new_piece()

        self.last_drop_ms = pygame.time.get_ticks()

    def get_cells(self, piece_type, rot, px, py):
        return [(px + x, py + y) for (x, y) in ROTATIONS[piece_type][rot]]

    def is_valid(self, piece_type, rot, px, py):
        for (x, y) in self.get_cells(piece_type, rot, px, py):
            if x < 0 or x >= COLS:
                return False
            if y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] != 0:
                return False
        return True

    def spawn_new_piece(self):
        self.curr_type = self.next_type
        self.next_type = self.get_next_type()
        self.px = 3
        self.py = -1
        self.rot = 0

        if not self.is_valid(self.curr_type, self.rot, self.px, self.py):
            self.game_over = True

    def try_move(self, dx, dy):
        new_px = self.px + dx
        new_py = self.py + dy
        if self.is_valid(self.curr_type, self.rot, new_px, new_py):
            self.px = new_px
            self.py = new_py
            return True
        return False

    def get_ghost_y(self):
        gy = self.py
        while self.is_valid(self.curr_type, self.rot, self.px, gy + 1):
            gy += 1
        return gy

    def lock_piece(self):
        idx = TYPE_TO_IDX[self.curr_type]
        for (x, y) in self.get_cells(self.curr_type, self.rot, self.px, self.py):
            if y < 0:
                continue
            self.board[y][x] = idx

    def clear_lines(self):
        new_board = []
        cleared = 0
        for y in range(ROWS):
            if all(self.board[y][x] != 0 for x in range(COLS)):
                cleared += 1
            else:
                new_board.append(self.board[y])

        while len(new_board) < ROWS:
            new_board.insert(0, [0 for _ in range(COLS)])

        # Apply the cleared rows immediately so blocks actually disappear.
        self.board = new_board

        if cleared > 0:
            self.lines += cleared
            # Each cleared line is worth exactly 1 point.
            self.score += cleared
            self.update_level()

    def update_level(self):
        # Increase every 10 cleared lines.
        self.level = self.lines // 10
        self.drop_interval_ms = max(100, 800 - self.level * 60)

    def rotate(self):
        new_rot = (self.rot + 1) % 4
        # Simple wall kicks (not full SRS, but sufficient for casual play)
        kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for (dx, dy) in kicks:
            if self.is_valid(self.curr_type, new_rot, self.px + dx, self.py + dy):
                self.rot = new_rot
                self.px += dx
                self.py += dy
                return True
        return False

    def soft_drop(self):
        if self.try_move(0, 1):
            return True
        return False

    def hard_drop(self):
        ghost_y = self.get_ghost_y()
        self.py = ghost_y
        self.lock_piece()
        self.clear_lines()
        if not self.game_over:
            self.spawn_new_piece()
        return True

    def tick(self):
        if self.game_over or self.paused:
            return
        # Try moving down; if blocked -> lock + clear + spawn
        if self.try_move(0, 1):
            return
        self.lock_piece()
        self.clear_lines()
        if self.game_over:
            return
        self.spawn_new_piece()


def draw_cell(screen, x, y, color, inset=2, border_width=0):
    rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
    if inset > 0:
        rect = rect.inflate(-2 * inset, -2 * inset)
    pygame.draw.rect(screen, color, rect, width=border_width)


def main():
    pygame.init()

    width = COLS * CELL + PANEL_W
    height = ROWS * CELL
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("俄罗斯方块 - pygame")
    clock = pygame.time.Clock()

    # Fonts
    font_title = pygame.font.Font(None, 22)
    font_stat = pygame.font.Font(None, 20)
    font_help = pygame.font.Font(None, 16)
    font_overlay = pygame.font.Font(None, 42)

    game = TetrisGame()
    game.reset()

    running = True
    while running:
        now_ms = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    continue

                if event.key == pygame.K_r:
                    game.reset()
                    continue

                if event.key == pygame.K_p:
                    if not game.game_over:
                        game.paused = not game.paused
                    continue

                if game.game_over or game.paused:
                    continue

                if event.key == pygame.K_LEFT:
                    game.try_move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.try_move(1, 0)
                elif event.key == pygame.K_DOWN:
                    game.soft_drop()
                elif event.key == pygame.K_UP:
                    game.rotate()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()

        # Drop timer
        if not game.game_over and not game.paused:
            if now_ms - game.last_drop_ms >= game.drop_interval_ms:
                game.tick()
                game.last_drop_ms = now_ms

        # Render
        screen.fill(GRID_BG)

        # Grid background lines
        for x in range(COLS + 1):
            pygame.draw.line(
                screen,
                GRID_LINE,
                (x * CELL, 0),
                (x * CELL, ROWS * CELL),
                1,
            )
        for y in range(ROWS + 1):
            pygame.draw.line(
                screen,
                GRID_LINE,
                (0, y * CELL),
                (COLS * CELL, y * CELL),
                1,
            )

        # Locked blocks
        for y in range(ROWS):
            for x in range(COLS):
                v = game.board[y][x]
                if v == 0:
                    continue
                draw_cell(screen, x, y, COLORS[v], inset=2, border_width=0)

        # Ghost
        if not game.game_over and game.curr_type is not None:
            ghost_y = game.get_ghost_y()
            ghost_color = COLORS[TYPE_TO_IDX[game.curr_type]]
            for (x, y) in game.get_cells(game.curr_type, game.rot, game.px, ghost_y):
                if y < 0:
                    continue
                # Draw ghost as outline rectangles
                draw_cell(screen, x, y, ghost_color, inset=3, border_width=2)

        # Active piece
        if not game.game_over and game.curr_type is not None:
            color = COLORS[TYPE_TO_IDX[game.curr_type]]
            for (x, y) in game.get_cells(game.curr_type, game.rot, game.px, game.py):
                if y < 0:
                    continue
                draw_cell(screen, x, y, color, inset=2, border_width=0)

        # Panel UI
        panel_x = COLS * CELL + 10
        title = font_title.render("TETRIS", True, TEXT_FG)
        screen.blit(title, (panel_x, 12))
        screen.blit(font_stat.render(f"Score: {game.score}", True, TEXT_FG), (panel_x, 42))
        screen.blit(font_stat.render(f"Level: {game.level}", True, TEXT_FG), (panel_x, 66))
        screen.blit(font_stat.render(f"Lines: {game.lines}", True, TEXT_FG), (panel_x, 90))

        screen.blit(font_stat.render("Next", True, TEXT_FG), (panel_x, 128))

        if game.next_type:
            mini_cell = int(CELL * 0.7)
            blocks = ROTATIONS[game.next_type][0]
            preview_x = panel_x + 5
            preview_y = 154
            val = TYPE_TO_IDX[game.next_type]
            fill = COLORS[val]
            for (x, y) in blocks:
                px = preview_x + x * mini_cell
                py = preview_y + y * mini_cell
                r = pygame.Rect(px + 2, py + 2, mini_cell - 4, mini_cell - 4)
                pygame.draw.rect(screen, fill, r)

        help_text = (
            "Move: \u2190 \u2192  Rotate: \u2191  Soft: \u2193  Hard: Space\n"
            "Pause: P  Restart: R  Quit: Esc"
        )
        # Render help at bottom of panel
        lines = help_text.splitlines()
        y0 = ROWS * CELL - 80
        for i, line in enumerate(lines):
            img = font_help.render(line, True, TEXT_FG)
            screen.blit(img, (panel_x, y0 + i * 20))

        # Overlays
        if game.paused and not game.game_over:
            overlay = pygame.Surface((COLS * CELL, ROWS * CELL), pygame.SRCALPHA)
            overlay.fill((*GRID_BG, 190))
            screen.blit(overlay, (0, 0))
            img = font_overlay.render("PAUSED", True, TEXT_FG)
            rect = img.get_rect(center=(COLS * CELL // 2, ROWS * CELL // 2))
            screen.blit(img, rect)
        if game.game_over:
            overlay = pygame.Surface((COLS * CELL, ROWS * CELL), pygame.SRCALPHA)
            overlay.fill((*GRID_BG, 190))
            screen.blit(overlay, (0, 0))
            img = font_overlay.render("GAME OVER", True, TEXT_FG)
            rect = img.get_rect(center=(COLS * CELL // 2, ROWS * CELL // 2 - 8))
            screen.blit(img, rect)
            img2 = font_help.render("Press R to restart", True, TEXT_FG)
            rect2 = img2.get_rect(center=(COLS * CELL // 2, ROWS * CELL // 2 + 34))
            screen.blit(img2, rect2)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

