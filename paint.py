import pygame
import sys
import datetime
import collections
import math

# Initialize Pygame
pygame.init()

# --- Constants & Configuration ---
WIDTH, HEIGHT = 900, 650  
TOOLBAR_HEIGHT = 160      
FPS = 120

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (220, 220, 220)
DARK_GRAY = (150, 150, 150)
LIGHT_BLUE = (200, 220, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

COLORS = [BLACK, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE]

# Tools
TOOL_BRUSH = 'brush'
TOOL_RECT = 'rect'
TOOL_FILL = 'fill'
TOOL_CIRCLE = 'circle' 
TOOL_TRIANGLE = 'triangle'
TOOL_TEXT = 'text'

# Setup Screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simple Paint - Swapped Rows")
clock = pygame.time.Clock()

# Fonts
font_sm = pygame.font.SysFont('Arial', 14)
font_bold = pygame.font.SysFont('Arial', 14, bold=True)
btn_font = pygame.font.SysFont('Arial', 13, bold=True)

# Layout Constants
# Row 2 (Now Tools)
ROW2_Y = 25
# Row 3 (Now Palette)
ROW3_Y = 65
# Row 4 (Picker)
ROW4_Y = 115

WHEEL_CENTER = (60, ROW4_Y + 22) 
WHEEL_RADIUS = 18 

def get_canvas_font(size):
    return pygame.font.SysFont('Arial', max(14, size * 4))

# --- Global State ---
drawing = False
start_pos = None  
last_pos = None   
brush_color = BLACK
brush_size = 5
eraser_mode = False
current_tool = TOOL_BRUSH

# Text Tool State
typing = False
text_input = ""
text_pos = (0, 0)

# Undo/Redo Stacks
undo_stack = []
redo_stack = []

# Define Button Areas (Now in Row 2)
BUTTON_Y = ROW2_Y + 5
BUTTON_HEIGHT = 30
BUTTON_W = 75

TEXT_TOOL_BTN_RECT = pygame.Rect(10, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
TRI_TOOL_BTN_RECT = pygame.Rect(90, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
CIRCLE_TOOL_BTN_RECT = pygame.Rect(170, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
FILL_TOOL_BTN_RECT = pygame.Rect(250, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
BRUSH_TOOL_BTN_RECT = pygame.Rect(330, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)
RECT_TOOL_BTN_RECT = pygame.Rect(410, BUTTON_Y, BUTTON_W, BUTTON_HEIGHT)

# Action Buttons on Right
UNDO_BTN_RECT = pygame.Rect(WIDTH - 220, BUTTON_Y, 65, BUTTON_HEIGHT)
REDO_BTN_RECT = pygame.Rect(WIDTH - 150, BUTTON_Y, 65, BUTTON_HEIGHT)
SAVE_BTN_RECT = pygame.Rect(WIDTH - 80, BUTTON_Y, 65, BUTTON_HEIGHT)

# Initialize Canvas
screen.fill(WHITE)

def draw_color_wheel(surface, center, radius):
    """Draws a radial color wheel."""
    for y in range(-radius, radius):
        for x in range(-radius, radius):
            dist = math.sqrt(x*x + y*y)
            if dist <= radius:
                angle = math.degrees(math.atan2(y, x)) % 360
                h = angle
                s = (dist / radius) * 100
                v = 100
                color = pygame.Color(0)
                color.hsva = (h, s, v, 100)
                surface.set_at((center[0] + x, center[1] + y), color)
    pygame.draw.circle(surface, BLACK, center, radius, 1)

def get_color_from_wheel(pos):
    """Returns color at pos if within wheel, else None."""
    dx = pos[0] - WHEEL_CENTER[0]
    dy = pos[1] - WHEEL_CENTER[1]
    dist = math.sqrt(dx*dx + dy*dy)
    if dist <= WHEEL_RADIUS:
        angle = math.degrees(math.atan2(dy, dx)) % 360
        s = (dist / WHEEL_RADIUS) * 100
        color = pygame.Color(0)
        color.hsva = (angle, s, 100, 100)
        return (color.r, color.g, color.b)
    return None

def draw_line(surface, start, end, width, color):
    pygame.draw.line(surface, color, start, end, width * 2)
    pygame.draw.circle(surface, color, start, width)
    pygame.draw.circle(surface, color, end, width)

def draw_rectangle_preview(surface, start, end, width, color):
    x1, y1 = start
    x2, y2 = end
    rect_x, rect_y = min(x1, x2), min(y1, y2)
    rect_w, rect_h = abs(x1 - x2), abs(y1 - y2)
    if rect_w > 0 and rect_h > 0:
        pygame.draw.rect(surface, color, (rect_x, rect_y, rect_w, rect_h), width)

def draw_circle_preview(surface, start, end, width, color):
    center_x, center_y = start
    radius = int(((end[0] - center_x)**2 + (end[1] - center_y)**2)**0.5)
    if radius > 0:
        pygame.draw.circle(surface, color, (center_x, center_y), radius, width)

def draw_triangle_preview(surface, start, end, width, color):
    x1, y1 = start
    x2, y2 = end
    p1 = (x1 + (x2 - x1) // 2, y1)
    p2 = (x1, y2)
    p3 = (x2, y2)
    pygame.draw.polygon(surface, color, [p1, p2, p3], width)

def flood_fill(surface, start_pos, replacement_color):
    if start_pos[1] <= TOOLBAR_HEIGHT: return
    try:
        target_color = tuple(surface.get_at(start_pos))[:3]
    except IndexError: return
    
    rep_color = pygame.Color(replacement_color)[:3]
    if target_color == rep_color: return
    
    queue = collections.deque([start_pos])
    max_x, max_y = surface.get_size()
    visited = {start_pos}
    
    while queue:
        x, y = queue.popleft()
        surface.set_at((x, y), rep_color)
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < max_x and TOOLBAR_HEIGHT < ny < max_y:
                if (nx, ny) not in visited and tuple(surface.get_at((nx, ny)))[:3] == target_color:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

def save_image():
    drawing_area = pygame.Rect(0, TOOLBAR_HEIGHT, WIDTH, HEIGHT - TOOLBAR_HEIGHT)
    sub = screen.subsurface(drawing_area)
    filename = f"drawing_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pygame.image.save(sub, filename)

def save_snapshot():
    if len(undo_stack) > 50: undo_stack.pop(0)
    undo_stack.append(screen.copy())
    redo_stack.clear()

def perform_undo():
    if undo_stack:
        redo_stack.append(screen.copy())
        screen.blit(undo_stack.pop(), (0, 0))

def perform_redo():
    if redo_stack:
        undo_stack.append(screen.copy())
        screen.blit(redo_stack.pop(), (0, 0))

def draw_button(surface, rect, text, active=True, toggled=False):
    color = (120, 140, 220) if toggled else (DARK_GRAY if active else (180, 180, 180))
    pygame.draw.rect(surface, color, rect, border_radius=3)
    pygame.draw.rect(surface, BLACK, rect, 1, border_radius=3)
    txt_surf = btn_font.render(text, True, WHITE if active or toggled else (100, 100, 100))
    surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))

def draw_ui(surface):
    # Main Toolbar background
    pygame.draw.rect(surface, GRAY, (0, 0, WIDTH, TOOLBAR_HEIGHT))
    
    # --- Row 1: Help & Status Bar ---
    pygame.draw.rect(surface, LIGHT_BLUE, (0, 0, WIDTH, 25))
    pygame.draw.line(surface, BLACK, (0, 25), (WIDTH, 25), 1)
    
    help_text = "C: Clear | ^Z: Undo | ^Y: Redo | +/-: Size | ENTER: Commit Text"
    surface.blit(font_sm.render(help_text, True, (40, 40, 40)), (10, 5))
    
    size_text = f"Brush Size: {brush_size}"
    size_surf = font_bold.render(size_text, True, BLACK)
    surface.blit(size_surf, (WIDTH - size_surf.get_width() - 10, 5))

    # --- Row 2: Tools & Actions (Previously Row 3) ---
    draw_button(surface, TEXT_TOOL_BTN_RECT, "TEXT", toggled=(current_tool == TOOL_TEXT))
    draw_button(surface, TRI_TOOL_BTN_RECT, "TRIANGLE", toggled=(current_tool == TOOL_TRIANGLE))
    draw_button(surface, CIRCLE_TOOL_BTN_RECT, "CIRCLE", toggled=(current_tool == TOOL_CIRCLE))
    draw_button(surface, FILL_TOOL_BTN_RECT, "FILL", toggled=(current_tool == TOOL_FILL))
    draw_button(surface, BRUSH_TOOL_BTN_RECT, "BRUSH", toggled=(current_tool == TOOL_BRUSH and not eraser_mode))
    draw_button(surface, RECT_TOOL_BTN_RECT, "RECT", toggled=(current_tool == TOOL_RECT))
    
    draw_button(surface, UNDO_BTN_RECT, "UNDO", active=len(undo_stack) > 0)
    draw_button(surface, REDO_BTN_RECT, "REDO", active=len(redo_stack) > 0)
    draw_button(surface, SAVE_BTN_RECT, "SAVE")

    # --- Row 3: Palette (Previously Row 2) ---
    pygame.draw.line(surface, DARK_GRAY, (0, ROW3_Y - 5), (WIDTH, ROW3_Y - 5), 1)
    for i, color in enumerate(COLORS):
        rect = pygame.Rect(10 + 40 * i, ROW3_Y + 5, 35, 25)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, BLACK, rect, 1)
        active_color = WHITE if eraser_mode else brush_color
        if not eraser_mode and color == active_color:
             pygame.draw.rect(surface, BLACK, rect, 2)
             pygame.draw.rect(surface, WHITE, rect.inflate(-4, -4), 1)

    # --- Row 4: Color Wheel & Preview ---
    pygame.draw.line(surface, DARK_GRAY, (0, ROW4_Y - 5), (WIDTH, ROW4_Y - 5), 1)
    
    draw_color_wheel(surface, WHEEL_CENTER, WHEEL_RADIUS)
    
    # Selected Color Preview
    preview_rect = pygame.Rect(100, ROW4_Y + 3, 35, 35) 
    if not eraser_mode:
        pygame.draw.rect(surface, brush_color, preview_rect)
        pygame.draw.rect(surface, BLACK, preview_rect, 2)
    else:
        pygame.draw.rect(surface, WHITE, preview_rect)
        pygame.draw.rect(surface, BLACK, preview_rect, 1)
        pygame.draw.line(surface, RED, preview_rect.topleft, preview_rect.bottomright, 2)
    
    pygame.draw.line(surface, BLACK, (0, TOOLBAR_HEIGHT), (WIDTH, TOOLBAR_HEIGHT), 2)

def commit_text():
    global typing, text_input
    if typing:
        if undo_stack: screen.blit(undo_stack[-1], (0, 0))
        if text_input.strip() != "":
            save_snapshot()
            canvas_font = get_canvas_font(brush_size)
            color = brush_color if not eraser_mode else WHITE
            txt_surface = canvas_font.render(text_input, True, color)
            screen.blit(txt_surface, text_pos)
    typing = False
    text_input = ""

def cancel_text():
    global typing, text_input
    if typing and undo_stack:
        screen.blit(undo_stack[-1], (0, 0))
    typing = False
    text_input = ""

def handle_ui_click(pos):
    global brush_color, eraser_mode, current_tool, typing
    x, y = pos

    # Check Color Wheel Area (Row 4)
    wheel_color = get_color_from_wheel(pos)
    if wheel_color:
        brush_color = wheel_color
        eraser_mode = False
        return

    # Check Toolbar Buttons (Now Row 2)
    if ROW2_Y <= y <= ROW2_Y + 45:
        if typing: commit_text()
        if SAVE_BTN_RECT.collidepoint(pos): save_image()
        elif UNDO_BTN_RECT.collidepoint(pos): perform_undo()
        elif REDO_BTN_RECT.collidepoint(pos): perform_redo()
        elif TEXT_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_TEXT
        elif TRI_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_TRIANGLE
        elif CIRCLE_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_CIRCLE
        elif FILL_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_FILL
        elif RECT_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_RECT
        elif BRUSH_TOOL_BTN_RECT.collidepoint(pos): current_tool = TOOL_BRUSH
        eraser_mode = False
    
    # Check Palette (Now Row 3)
    elif ROW3_Y <= y <= ROW3_Y + 45:
        for i, color in enumerate(COLORS):
            rect_x = 10 + 40 * i
            if rect_x <= x <= rect_x + 35:
                if color == WHITE: 
                    eraser_mode = True
                else:
                    eraser_mode = False
                    brush_color = color
                return

# --- Main Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        elif event.type == pygame.KEYDOWN:
            if typing:
                if event.key == pygame.K_RETURN: commit_text()
                elif event.key == pygame.K_BACKSPACE: text_input = text_input[:-1]
                elif event.key == pygame.K_ESCAPE: cancel_text()
                elif event.unicode.isprintable(): text_input += event.unicode
            else:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_c:
                    save_snapshot(); screen.fill(WHITE)
                elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL): perform_undo()
                elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL): perform_redo()
                elif event.key in [pygame.K_EQUALS, pygame.K_KP_PLUS]: brush_size = min(50, brush_size + 1)
                elif event.key in [pygame.K_MINUS, pygame.K_KP_MINUS]: brush_size = max(1, brush_size - 1)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                if event.pos[1] <= TOOLBAR_HEIGHT:
                    handle_ui_click(event.pos)
                else:
                    if current_tool == TOOL_TEXT:
                        if typing: commit_text()
                        save_snapshot()
                        typing = True
                        text_input = ""
                        text_pos = event.pos
                    else:
                        if typing: commit_text()
                        save_snapshot()
                        if current_tool == TOOL_FILL:
                            flood_fill(screen, event.pos, WHITE if eraser_mode else brush_color)
                        else:
                            drawing = True
                            start_pos = last_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: 
                drawing = False
                start_pos = None

        elif event.type == pygame.MOUSEMOTION:
            if drawing and event.pos[1] > TOOLBAR_HEIGHT:
                color = WHITE if eraser_mode else brush_color
                if current_tool == TOOL_BRUSH:
                    draw_line(screen, last_pos, event.pos, brush_size, color)
                    last_pos = event.pos
                elif current_tool in [TOOL_RECT, TOOL_CIRCLE, TOOL_TRIANGLE]:
                    if undo_stack: screen.blit(undo_stack[-1], (0, 0))
                    if current_tool == TOOL_RECT: draw_rectangle_preview(screen, start_pos, event.pos, brush_size, color)
                    elif current_tool == TOOL_CIRCLE: draw_circle_preview(screen, start_pos, event.pos, brush_size, color)
                    elif current_tool == TOOL_TRIANGLE: draw_triangle_preview(screen, start_pos, event.pos, brush_size, color)

    draw_ui(screen)
    
    if typing:
        if undo_stack: screen.blit(undo_stack[-1], (0, 0))
        draw_ui(screen)
        canvas_font = get_canvas_font(brush_size)
        color = brush_color if not eraser_mode else (50, 50, 50)
        cursor = "_" if (pygame.time.get_ticks() // 400) % 2 == 0 else " "
        preview_surf = canvas_font.render(text_input + cursor, True, color)
        bg_rect = preview_surf.get_rect(topleft=text_pos)
        pygame.draw.rect(screen, (240, 240, 240), bg_rect.inflate(4, 4))
        pygame.draw.rect(screen, (100, 100, 100), bg_rect.inflate(4, 4), 1)
        screen.blit(preview_surf, text_pos)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()