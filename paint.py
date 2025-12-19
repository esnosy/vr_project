import pygame
import sys
import datetime
import collections  # Import for the flood fill queue

# Initialize Pygame
pygame.init()

# --- Constants & Configuration ---
WIDTH, HEIGHT = 900, 600
TOOLBAR_HEIGHT = 110  # Increased height for two rows
FPS = 120

# Colors (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (150, 150, 150)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

# List of selectable colors
COLORS = [BLACK, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE]

# Tools
TOOL_BRUSH = 'brush'
TOOL_RECT = 'rect'
TOOL_FILL = 'fill'
TOOL_CIRCLE = 'circle'

# Setup Screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simple Paint - Two-Row Toolbar")
clock = pygame.time.Clock()

# Font
font = pygame.font.SysFont('Arial', 16)
btn_font = pygame.font.SysFont('Arial', 14, bold=True)

# --- Global State ---
drawing = False
start_pos = None  # To store the initial click position for shapes
last_pos = None   # To store the previous mouse position for brush continuity
brush_color = BLACK
brush_size = 5
eraser_mode = False
current_tool = TOOL_BRUSH

# Undo/Redo Stacks
undo_stack = []
redo_stack = []

# Define Button Areas (Spaced out from right to left, all on the second row)
BUTTON_Y = 65
BUTTON_HEIGHT = 40
BUTTON_W = 70

# Tools (Left side of 2nd row - from left to right in the UI)
CIRCLE_TOOL_BTN_RECT = pygame.Rect(
    WIDTH - 560, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
FILL_TOOL_BTN_RECT = pygame.Rect(
    WIDTH - 480, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
BRUSH_TOOL_BTN_RECT = pygame.Rect(
    WIDTH - 400, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
RECT_TOOL_BTN_RECT = pygame.Rect(
    WIDTH - 320, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)

# Actions (Right side of 2nd row)
UNDO_BTN_RECT = pygame.Rect(WIDTH - 240, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
REDO_BTN_RECT = pygame.Rect(WIDTH - 160, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
SAVE_BTN_RECT = pygame.Rect(WIDTH - 80, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)

# Initialize Canvas (Background)
screen.fill(WHITE)


def draw_line(surface, start, end, width, color):
    """Draws a line with rounded caps."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = max(abs(dx), abs(dy))

    for i in range(distance):
        x = int(start[0] + float(i) / distance * dx)
        y = int(start[1] + float(i) / distance * dy)
        pygame.draw.circle(surface, color, (x, y), width)


def draw_rectangle_preview(surface, start, end, width, color):
    """Draws a rectangle from start pos to end pos."""
    # Calculate rect dimensions
    x1, y1 = start
    x2, y2 = end

    # Determine top-left corner and dimensions
    rect_x = min(x1, x2)
    rect_y = min(y1, y2)
    rect_w = abs(x1 - x2)
    rect_h = abs(y1 - y2)

    pygame.draw.rect(surface, color, (rect_x, rect_y, rect_w, rect_h), width)


def draw_circle_preview(surface, start, end, width, color):
    """Draws a circle using start point as center and distance to end point as radius."""
    center_x, center_y = start
    end_x, end_y = end

    # Calculate radius using distance formula: sqrt((x2-x1)^2 + (y2-y1)^2)
    radius = int(((end_x - center_x)**2 + (end_y - center_y)**2)**0.5)

    # Pygame expects the center as a tuple, and radius as an integer
    # Ensure radius is non-negative
    radius = max(1, radius)
    pygame.draw.circle(surface, color, (center_x, center_y), radius, width)


def flood_fill(surface, start_pos, replacement_color):
    """Performs an iterative flood fill (BFS) starting at start_pos."""

    # If the start position is in the toolbar, do nothing
    if start_pos[1] <= TOOLBAR_HEIGHT:
        return

    try:
        # Get the color of the start pixel (the color to be replaced)
        target_color = tuple(surface.get_at(start_pos))[:3]
    except IndexError:
        return  # Safety check

    # If the target color is already the replacement color, do nothing
    if target_color == tuple(replacement_color)[:3]:
        return

    # Setup the queue for BFS
    queue = collections.deque([start_pos])

    # Boundaries and constraints
    max_x, max_y = surface.get_size()
    min_y = TOOLBAR_HEIGHT

    # Color check function: Checks if the color at (x, y) matches the target color
    def matches_target(x, y):
        # Bounds check is done in the main loop for performance
        if x < 0 or x >= max_x or y < min_y or y >= max_y:
            return False

        current_color = tuple(surface.get_at((x, y)))[:3]
        return current_color == target_color

    while queue:
        x, y = queue.popleft()

        # Check bounds and if we should fill this pixel
        if matches_target(x, y):
            # Fill the pixel
            surface.set_at((x, y), replacement_color)

            # Add neighbors (4 directions) to the queue for checking
            queue.append((x + 1, y))
            queue.append((x - 1, y))
            queue.append((x, y + 1))
            queue.append((x, y - 1))


def save_image():
    """Saves the drawing area (excluding toolbar) to a file."""
    drawing_area = pygame.Rect(
        0, TOOLBAR_HEIGHT, WIDTH, HEIGHT - TOOLBAR_HEIGHT)
    sub = screen.subsurface(drawing_area)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"drawing_{timestamp}.png"
    pygame.image.save(sub, filename)
    print(f"Image saved as {filename}")


def save_snapshot():
    """Saves the current screen state to the undo stack."""
    # Limit stack size to avoid excessive memory usage (e.g. 50 steps)
    if len(undo_stack) > 50:
        undo_stack.pop(0)

    # Copy the entire surface
    undo_stack.append(screen.copy())
    # New action clears the redo history
    redo_stack.clear()


def perform_undo():
    """Restores the previous state."""
    if undo_stack:
        # Save current state to redo stack before undoing
        redo_stack.append(screen.copy())

        # Pop the last state and blit it to screen
        prev_state = undo_stack.pop()
        screen.blit(prev_state, (0, 0))


def perform_redo():
    """Re-applies a previously undone state."""
    if redo_stack:
        # Save current state to undo stack before redoing
        undo_stack.append(screen.copy())

        # Pop the redo state and blit it to screen
        next_state = redo_stack.pop()
        screen.blit(next_state, (0, 0))


def draw_button(surface, rect, text, active=True, toggled=False):
    """Helper to draw standardized buttons."""
    # Change color if toggled (selected)
    if toggled:
        color = (100, 100, 200)  # Blue-ish for selected tool
        text_color = WHITE
    elif active:
        color = DARK_GRAY
        text_color = WHITE
    else:
        color = GRAY
        text_color = (100, 100, 100)

    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, BLACK, rect, 1)  # Border

    txt_surf = btn_font.render(text, True, text_color)
    text_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, text_rect)


def draw_ui(surface):
    """Draws the toolbar, palette, and buttons."""
    # Draw Toolbar Background - uses the new, larger TOOLBAR_HEIGHT
    pygame.draw.rect(surface, GRAY, (0, 0, WIDTH, TOOLBAR_HEIGHT))
    pygame.draw.line(surface, BLACK, (0, TOOLBAR_HEIGHT),
                     (WIDTH, TOOLBAR_HEIGHT), 2)

    # --- Top Row: Color Palette (Y=10) ---
    swatch_size = 40
    padding = 10
    start_x = 10

    for i, color in enumerate(COLORS):
        rect_x = start_x + (swatch_size + padding) * i
        rect_y = 10  # First Row Y

        pygame.draw.rect(
            surface, color, (rect_x, rect_y, swatch_size, swatch_size))
        pygame.draw.rect(surface, BLACK, (rect_x, rect_y,
                         swatch_size, swatch_size), 1)

        # Highlight selected color
        current_selection = WHITE if eraser_mode else brush_color
        if color == current_selection:
            pygame.draw.rect(surface, WHITE, (rect_x, rect_y,
                             swatch_size, swatch_size), 3)

    # --- Top Row: Controls Info ---
    # Draw info immediately after colors, with less padding
    controls_x = start_x + (swatch_size + padding) * len(COLORS) + 15

    # Brush Size Display (Y=20)
    size_text = font.render(f"Size: {brush_size}", True, BLACK)
    surface.blit(size_text, (controls_x, 20))

    # Instructions (Y=20)
    help_text = font.render("C: Clr | ^Z: Undo", True, (60, 60, 60))
    surface.blit(help_text, (controls_x + 60, 20))

    # --- Second Row: Buttons (Drawn using their predefined Rects on Y=65) ---

    # Tools (Left side of 2nd row)
    draw_button(surface, CIRCLE_TOOL_BTN_RECT, "CIRCLE",
                toggled=(current_tool == TOOL_CIRCLE))
    draw_button(surface, FILL_TOOL_BTN_RECT, "FILL",
                toggled=(current_tool == TOOL_FILL))
    draw_button(surface, BRUSH_TOOL_BTN_RECT, "BRUSH", toggled=(
        current_tool == TOOL_BRUSH and not eraser_mode))
    draw_button(surface, RECT_TOOL_BTN_RECT, "RECT",
                toggled=(current_tool == TOOL_RECT))

    # Actions (Right side of 2nd row)
    draw_button(surface, UNDO_BTN_RECT, "UNDO", active=len(undo_stack) > 0)
    draw_button(surface, REDO_BTN_RECT, "REDO", active=len(redo_stack) > 0)
    draw_button(surface, SAVE_BTN_RECT, "SAVE")


def handle_ui_click(pos):
    """Handles clicks inside the toolbar area."""
    global brush_color, eraser_mode, current_tool

    x, y = pos

    # 1. Check Buttons (Second Row Check: Y >= 65)
    if y >= 65:
        if SAVE_BTN_RECT.collidepoint(pos):
            save_image()
            return
        elif UNDO_BTN_RECT.collidepoint(pos):
            perform_undo()
            return
        elif REDO_BTN_RECT.collidepoint(pos):
            perform_redo()
            return
        elif CIRCLE_TOOL_BTN_RECT.collidepoint(pos):
            current_tool = TOOL_CIRCLE
            eraser_mode = False
            return
        elif FILL_TOOL_BTN_RECT.collidepoint(pos):
            current_tool = TOOL_FILL
            eraser_mode = False
            return
        elif RECT_TOOL_BTN_RECT.collidepoint(pos):
            current_tool = TOOL_RECT
            eraser_mode = False
            return
        elif BRUSH_TOOL_BTN_RECT.collidepoint(pos):
            current_tool = TOOL_BRUSH
            eraser_mode = False
            return

    # 2. Check Color Palette (First Row Check: Y <= 50)
    elif y <= 50:
        swatch_size = 40
        padding = 10
        start_x = 10

        for i, color in enumerate(COLORS):
            rect_x = start_x + (swatch_size + padding) * i
            if rect_x <= x <= rect_x + swatch_size and 10 <= y <= 10 + swatch_size:
                if color == WHITE:
                    eraser_mode = True
                    current_tool = TOOL_BRUSH
                else:
                    eraser_mode = False
                    brush_color = color
                    # Only switch back to brush tool if we weren't using a shape tool before
                    if current_tool != TOOL_RECT and current_tool != TOOL_CIRCLE:
                        current_tool = TOOL_BRUSH
                return


# --- Main Loop ---
running = True
while running:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if event.pos[1] <= TOOLBAR_HEIGHT:
                    handle_ui_click(event.pos)
                else:
                    # Clicked on Canvas - Save state BEFORE action
                    save_snapshot()

                    if current_tool == TOOL_FILL:
                        # Execute flood fill immediately on click
                        color_to_use = WHITE if eraser_mode else brush_color
                        flood_fill(screen, event.pos, color_to_use)
                        # Flood fill is a single action, no drag needed.
                        drawing = False
                    else:
                        # Start drag for Brush, Rect, or Circle
                        drawing = True
                        start_pos = event.pos  # Remember where we started clicking
                        last_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                drawing = False
                # Reset start_pos/last_pos after finishing the stroke/shape/fill
                start_pos = None
                last_pos = None

        elif event.type == pygame.MOUSEMOTION:
            if drawing and current_tool != TOOL_FILL:  # Fill tool doesn't use mouse motion
                current_pos = event.pos

                # Prevent drawing into toolbar
                if current_pos[1] > TOOLBAR_HEIGHT:
                    color_to_use = WHITE if eraser_mode else brush_color

                    if current_tool == TOOL_BRUSH:
                        # Standard Brush Logic
                        if last_pos:
                            draw_line(screen, last_pos, current_pos,
                                      brush_size, color_to_use)
                        else:
                            pygame.draw.circle(
                                screen, color_to_use, current_pos, brush_size)
                        last_pos = current_pos

                    elif current_tool == TOOL_RECT:
                        # Rectangle Logic - Live Preview
                        # 1. Restore the screen to what it was BEFORE we started dragging this rect
                        if undo_stack:
                            screen.blit(undo_stack[-1], (0, 0))

                        # 2. Draw the rectangle at the new size
                        draw_rectangle_preview(
                            screen, start_pos, current_pos, brush_size, color_to_use)

                    elif current_tool == TOOL_CIRCLE:
                        # Circle Logic - Live Preview
                        # 1. Restore the screen to what it was BEFORE we started dragging this shape
                        if undo_stack:
                            screen.blit(undo_stack[-1], (0, 0))

                        # 2. Draw the circle
                        draw_circle_preview(
                            screen, start_pos, current_pos, brush_size, color_to_use)

        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            if event.key == pygame.K_c:
                save_snapshot()
                screen.fill(WHITE)

            elif event.key == pygame.K_e:
                eraser_mode = not eraser_mode
                current_tool = TOOL_BRUSH  # Eraser forces brush tool

            elif event.key == pygame.K_s:
                save_image()

            elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                perform_undo()

            elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                perform_redo()

            elif event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:
                brush_size = min(50, brush_size + 1)

            elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                brush_size = max(1, brush_size - 1)

    # 2. Draw UI
    draw_ui(screen)

    # 3. Update Display
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
