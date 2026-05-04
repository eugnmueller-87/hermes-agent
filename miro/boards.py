from datetime import datetime, timezone
from .client import MiroClient, URGENCY_COLOR, SIGNAL_THEME
from storage.redis_store import RedisStore
from config.suppliers import ALL_SUPPLIERS
from collections import defaultdict

FRAME_W = 960
FRAME_H = 720
FRAME_GAP_X = 1100
FRAME_GAP_Y = 820
COLS = 3
NOTE_W = 210
NOTE_H = 210
NOTE_GAP = 220
NOTES_PER_ROW = 4


def _frame_pos(index: int):
    col = index % COLS
    row = index // COLS
    return col * FRAME_GAP_X, row * FRAME_GAP_Y


def _note_positions(frame_x: int, frame_y: int, count: int):
    positions = []
    start_x = frame_x - (FRAME_W // 2) + NOTE_W // 2 + 30
    start_y = frame_y - (FRAME_H // 2) + NOTE_H // 2 + 80  # leave room for frame title
    for i in range(count):
        col = i % NOTES_PER_ROW
        row = i // NOTES_PER_ROW
        positions.append((start_x + col * NOTE_GAP, start_y + row * NOTE_GAP))
    return positions


def build_signal_board(store: RedisStore) -> str:
    """
    Creates a Miro board of today's significant Hermes signals.
    One frame per signal type, sticky notes colored by urgency.
    Returns the board URL.
    """
    client = MiroClient()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    board = client.create_board(
        name=f"Hermes Signal Board — {today}",
        description="Significant market intelligence signals from Hermes. Generated automatically.",
    )
    board_id = board["id"]
    url = client.get_board_url(board)
    print(f"[Miro] Board created: {url}")

    items = store.get_significant_items(limit=100)
    if not items:
        print("[Miro] No significant items found in Redis")
        return url

    by_signal = defaultdict(list)
    for item in items:
        by_signal[item.get("signal_type", "OTHER")].append(item)

    for frame_index, (signal_type, signal_items) in enumerate(sorted(by_signal.items())):
        fx, fy = _frame_pos(frame_index)
        emoji = signal_items[0].get("emoji", "📰")
        client.create_frame(board_id, f"{emoji} {signal_type} ({len(signal_items)})", fx, fy, FRAME_W, FRAME_H)

        positions = _note_positions(fx, fy, len(signal_items))
        for item, (nx, ny) in zip(signal_items, positions):
            content = f"{item['supplier']}\n\n{item['title'][:120]}"
            if item.get("significance_reason"):
                content += f"\n\n{item['significance_reason'][:80]}"
            color = URGENCY_COLOR.get(item.get("urgency", "LOW"), "yellow")
            client.create_sticky_note(board_id, content, nx, ny, color)

        print(f"[Miro] Frame '{signal_type}': {len(signal_items)} notes")

    print(f"[Miro] Signal board done — {len(items)} items across {len(by_signal)} signal types")
    return url


def build_landscape_board(store: RedisStore, category_filter: str = None) -> str:
    """
    Creates a Miro competitive landscape board.
    One frame per category, cards for each supplier showing latest signal.
    Pass category_filter to limit to one category (e.g. 'AI Foundation Labs').
    Returns the board URL.
    """
    client = MiroClient()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    title = f"Hermes Landscape — {category_filter or 'All Categories'} — {today}"
    board = client.create_board(
        name=title,
        description="Competitive landscape from Hermes supplier coverage.",
    )
    board_id = board["id"]
    url = client.get_board_url(board)
    print(f"[Miro] Board created: {url}")

    by_category = defaultdict(list)
    for s in ALL_SUPPLIERS:
        cat = s.get("category", "Other")
        if category_filter and cat != category_filter:
            continue
        by_category[cat].append(s)

    CARD_W = 280
    CARD_H = 90
    CARD_GAP_X = 300
    CARD_GAP_Y = 100
    CARDS_PER_ROW = 3
    LANDSCAPE_FRAME_W = CARDS_PER_ROW * CARD_GAP_X + 80
    LANDSCAPE_FRAME_H = 800

    for frame_index, (category, suppliers) in enumerate(sorted(by_category.items())):
        fx, fy = _frame_pos(frame_index)
        fw = LANDSCAPE_FRAME_W
        fh = min(LANDSCAPE_FRAME_H, ((len(suppliers) // CARDS_PER_ROW) + 1) * CARD_GAP_Y + 150)
        client.create_frame(board_id, category, fx, fy, fw, fh)

        start_x = fx - fw // 2 + CARD_W // 2 + 30
        start_y = fy - fh // 2 + CARD_H // 2 + 80

        for i, supplier in enumerate(suppliers):
            col = i % CARDS_PER_ROW
            row = i // CARDS_PER_ROW
            cx = start_x + col * CARD_GAP_X
            cy = start_y + row * CARD_GAP_Y

            latest = store.get_supplier_items(supplier["name"], limit=1)
            if latest:
                desc = f"T{supplier.get('tier', '?')} · {latest[0].get('emoji','📰')} {latest[0].get('signal_type','OTHER')}"
            else:
                desc = f"T{supplier.get('tier', '?')} · No recent signals"

            tier = supplier.get("tier", 3)
            color = {"1": "#e74c3c", "2": "#f39c12", "3": "#95a5a6"}.get(str(tier), "#95a5a6")
            client.create_card(board_id, supplier["name"], desc, cx, cy, color)

        print(f"[Miro] Frame '{category}': {len(suppliers)} suppliers")

    print(f"[Miro] Landscape board done — {len(by_category)} categories")
    return url
