#!/usr/bin/env python3
import random
import tkinter as tk


COLS = 10
ROWS = 20
CELL = 24

PANEL_W = 200
FPS = 60

# Board values are 0 (empty) or 1..7 (tetromino index)
TYPES = ["I", "J", "L", "O", "S", "T", "Z"]
TYPE_TO_IDX = {t: i + 1 for i, t in enumerate(TYPES)}

COLORS = {
    # idx -> color
    TYPE_TO_IDX["I"]: "#00E5FF",
    TYPE_TO_IDX["J"]: "#3F51B5",
    TYPE_TO_IDX["L"]: "#FF9800",
    TYPE_TO_IDX["O"]: "#FFEB3B",
    TYPE_TO_IDX["S"]: "#4CAF50",
    TYPE_TO_IDX["T"]: "#9C27B0",
    TYPE_TO_IDX["Z"]: "#F44336",
}

GRID_BG = "#0f0f12"
GRID_LINE = "#1c1c22"
TEXT_FG = "#eaeaf0"


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
    # Each piece is defined inside a 4x4 grid.
    # Coordinates are relative to the piece position (px, py).
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
}

ROTATIONS = {t: build_rotations(SHAPES_4X4[t]) for t in TYPES}


class TetrisApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("俄罗斯方块 - Python tkinter")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=COLS * CELL + PANEL_W,
            height=ROWS * CELL,
            bg=GRID_BG,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.score = 0
        self.level = 0
        self.lines = 0

        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = []

        self.curr_type = None
        self.next_type = None
        self.px = 3  # left position in grid
        self.py = -1  # top position in grid (can be negative on spawn)
        self.rot = 0

        self.game_over = False
        self.paused = False
        self.after_id = None

        self.drop_interval_ms = 800

        self._bind_keys()
        self.start_new_game()
        self.draw()
        self.schedule_tick()

    def _bind_keys(self):
        # Use key symbols from Tk
        self.root.bind("<Left>", lambda e: self.handle_move(-1, 0))
        self.root.bind("<Right>", lambda e: self.handle_move(1, 0))
        self.root.bind("<Down>", lambda e: self.handle_soft_drop())
        self.root.bind("<Up>", lambda e: self.handle_rotate())
        self.root.bind("<space>", lambda e: self.handle_hard_drop())
        self.root.bind("p", lambda e: self.toggle_pause())
        self.root.bind("P", lambda e: self.toggle_pause())
        self.root.bind("r", lambda e: self.start_new_game())
        self.root.bind("R", lambda e: self.start_new_game())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def make_shuffled_bag(self):
        bag = TYPES[:]
        random.shuffle(bag)
        return bag

    def get_next_type(self):
        if not self.bag:
            self.bag = self.make_shuffled_bag()
        return self.bag.pop()

    def start_new_game(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

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

        self.draw()
        self.schedule_tick()

    def schedule_tick(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
        self.after_id = self.root.after(self.drop_interval_ms, self.tick)

    def tick(self):
        self.after_id = None
        if self.game_over or self.paused:
            self.schedule_tick()
            return

        if self.try_move(0, 1):
            self.draw()
            self.schedule_tick()
            return

        self.lock_piece()
        self.clear_lines()
        if self.game_over:
            self.draw()
            return

        self.spawn_new_piece()
        self.draw()
        self.schedule_tick()

    def spawn_new_piece(self):
        self.curr_type = self.next_type
        self.next_type = self.get_next_type()
        self.px = 3
        self.py = -1
        self.rot = 0

        if not self.is_valid(self.curr_type, self.rot, self.px, self.py):
            self.game_over = True
            self.paused = False

    def toggle_pause(self):
        if self.game_over:
            return
        self.paused = not self.paused
        self.draw()
        if not self.paused:
            self.schedule_tick()

    def get_cells(self, piece_type, rot, px, py):
        cells = []
        for (x, y) in ROTATIONS[piece_type][rot]:
            cells.append((px + x, py + y))
        return cells

    def is_valid(self, piece_type, rot, px, py):
        for (x, y) in self.get_cells(piece_type, rot, px, py):
            if x < 0 or x >= COLS:
                return False
            if y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] != 0:
                return False
        return True

    def try_move(self, dx, dy):
        new_px = self.px + dx
        new_py = self.py + dy
        if self.is_valid(self.curr_type, self.rot, new_px, new_py):
            self.px = new_px
            self.py = new_py
            return True
        return False

    def handle_move(self, dx, dy):
        if self.game_over or self.paused:
            return
        if self.try_move(dx, dy):
            self.draw()

    def handle_soft_drop(self):
        if self.game_over or self.paused:
            return
        if self.try_move(0, 1):
            self.draw()

    def get_ghost_y(self):
        gy = self.py
        while self.is_valid(self.curr_type, self.rot, self.px, gy + 1):
            gy += 1
        return gy

    def handle_hard_drop(self):
        if self.game_over or self.paused:
            return
        ghost_y = self.get_ghost_y()
        self.py = ghost_y
        self.lock_piece()
        self.clear_lines()
        if not self.game_over:
            self.spawn_new_piece()
        self.draw()
        self.schedule_tick()

    def handle_rotate(self):
        if self.game_over or self.paused:
            return
        new_rot = (self.rot + 1) % 4

        # Simple wall kicks (not full SRS, but works well enough for casual play)
        kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for (dx, dy) in kicks:
            if self.is_valid(self.curr_type, new_rot, self.px + dx, self.py + dy):
                self.rot = new_rot
                self.px += dx
                self.py += dy
                self.draw()
                return

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

        # Add empty rows on top
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
        # Simple leveling: increase every 10 cleared lines
        self.level = self.lines // 10
        self.drop_interval_ms = max(100, 800 - self.level * 60)

    def color_for_cell(self, cell_val):
        if cell_val == 0:
            return None
        return COLORS.get(cell_val, "#ffffff")

    def draw_block(self, x, y, fill, outline=None, width=2):
        x0 = x * CELL
        y0 = y * CELL
        x1 = x0 + CELL
        y1 = y0 + CELL
        self.canvas.create_rectangle(
            x0 + 2,
            y0 + 2,
            x1 - 2,
            y1 - 2,
            fill=fill,
            outline=outline if outline else fill,
            width=width,
        )

    def draw_grid_lines(self):
        for x in range(COLS + 1):
            self.canvas.create_line(x * CELL, 0, x * CELL, ROWS * CELL, fill=GRID_LINE, width=1)
        for y in range(ROWS + 1):
            self.canvas.create_line(0, y * CELL, COLS * CELL, y * CELL, fill=GRID_LINE, width=1)

    def draw_preview_box(self, piece_type, offset_x, offset_y, scale=0.7):
        # Draw tetromino in a 4x4 mini grid
        mini_cell = int(CELL * scale)
        blocks = ROTATIONS[piece_type][0]
        # Compute bounding box inside 4x4
        for (x, y) in blocks:
            px = offset_x + x * mini_cell
            py = offset_y + y * mini_cell
            val = TYPE_TO_IDX[piece_type]
            fill = COLORS[val]
            self.canvas.create_rectangle(
                px + 2,
                py + 2,
                px + mini_cell - 2,
                py + mini_cell - 2,
                fill=fill,
                outline=fill,
                width=1,
            )

    def draw(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            0,
            0,
            COLS * CELL,
            ROWS * CELL,
            fill=GRID_BG,
            outline=GRID_BG,
        )

        # Grid background lines
        self.draw_grid_lines()

        # Locked board
        for y in range(ROWS):
            for x in range(COLS):
                v = self.board[y][x]
                if v == 0:
                    continue
                color = self.color_for_cell(v)
                if color:
                    self.draw_block(x, y, fill=color, outline=color, width=0)

        # Ghost
        if not self.game_over:
            ghost_y = self.get_ghost_y()
            ghost_outline = self.color_for_cell(TYPE_TO_IDX[self.curr_type]) or "#ffffff"
            for (x, y) in self.get_cells(self.curr_type, self.rot, self.px, ghost_y):
                if y < 0:
                    continue
                self.draw_block(x, y, fill=ghost_outline, outline=ghost_outline, width=2)

        # Active piece
        if self.curr_type and not self.game_over:
            color = self.color_for_cell(TYPE_TO_IDX[self.curr_type]) or "#ffffff"
            for (x, y) in self.get_cells(self.curr_type, self.rot, self.px, self.py):
                if y < 0:
                    continue
                self.draw_block(x, y, fill=color, outline=color, width=0)

        # UI Panel
        ui_x = COLS * CELL + 20
        self.canvas.create_text(ui_x, 20, anchor="nw", fill=TEXT_FG, font=("Arial", 16, "bold"), text="TETRIS")
        self.canvas.create_text(ui_x, 50, anchor="nw", fill=TEXT_FG, font=("Arial", 12), text=f"Score: {self.score}")
        self.canvas.create_text(ui_x, 75, anchor="nw", fill=TEXT_FG, font=("Arial", 12), text=f"Level: {self.level}")
        self.canvas.create_text(ui_x, 100, anchor="nw", fill=TEXT_FG, font=("Arial", 12), text=f"Lines: {self.lines}")

        self.canvas.create_text(ui_x, 140, anchor="nw", fill=TEXT_FG, font=("Arial", 12, "bold"), text="Next")
        if self.next_type:
            self.draw_preview_box(self.next_type, ui_x + 5, 160)

        help_y = ROWS * CELL - 90
        self.canvas.create_text(
            ui_x,
            help_y,
            anchor="nw",
            fill=TEXT_FG,
            font=("Arial", 10),
            text="Move: ← →  Rotate: ↑  Soft: ↓  Hard: Space\nPause: P  Restart: R  Quit: Esc",
        )

        if self.paused and not self.game_over:
            self.canvas.create_rectangle(0, 0, COLS * CELL, ROWS * CELL, fill=GRID_BG, outline="")
            self.canvas.create_text(
                COLS * CELL // 2,
                ROWS * CELL // 2,
                fill=TEXT_FG,
                font=("Arial", 24, "bold"),
                text="PAUSED",
            )

        if self.game_over:
            self.canvas.create_rectangle(0, 0, COLS * CELL, ROWS * CELL, fill=GRID_BG, outline="")
            self.canvas.create_text(
                COLS * CELL // 2,
                ROWS * CELL // 2 - 10,
                fill=TEXT_FG,
                font=("Arial", 24, "bold"),
                text="GAME OVER",
            )
            self.canvas.create_text(
                COLS * CELL // 2,
                ROWS * CELL // 2 + 20,
                fill=TEXT_FG,
                font=("Arial", 12),
                text="Press R to restart",
            )


def main():
    root = tk.Tk()
    app = TetrisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

