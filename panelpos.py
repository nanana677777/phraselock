"""Where the phrase panel sits on the lock screen (center, top, bottom or a custom spot)."""

POSITIONS = ("center", "top", "bottom", "custom")
MARGIN_FRACTION = 0.06      # gap kept above (top) or below (bottom) the panel, as a share of the screen height


def _percent(value, default=50):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def panel_origin(position, screen_w, screen_h, panel_w, panel_h, custom_x=50, custom_y=50):
    """(x, y) of the panel's top-left corner. The panel always stays fully on the screen.

    custom_x / custom_y are percentages (0 = left/top edge, 100 = right/bottom edge) of the free room.
    An unknown *position* falls back to the centre.
    """
    room_x = max(0, screen_w - panel_w)
    room_y = max(0, screen_h - panel_h)
    x = room_x // 2
    y = room_y // 2
    if position == "top":
        y = min(room_y, int(screen_h * MARGIN_FRACTION))
    elif position == "bottom":
        y = max(0, room_y - int(screen_h * MARGIN_FRACTION))
    elif position == "custom":
        x = room_x * _percent(custom_x) // 100
        y = room_y * _percent(custom_y) // 100
    return x, y


def normalize_position(value):
    return value if value in POSITIONS else "center"
