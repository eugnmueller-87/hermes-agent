import os
import httpx

BASE_URL = "https://api.miro.com/v2"

URGENCY_COLOR = {
    "HIGH":   "red",
    "MEDIUM": "yellow",
    "LOW":    "light_green",
}

SIGNAL_THEME = {
    "FUNDING":        "#f5a623",
    "ACQUISITION":    "#7ed321",
    "PRODUCT_RELEASE":"#4a90e2",
    "PRICING_CHANGE": "#9b59b6",
    "SUPPLY_CHAIN":   "#e74c3c",
    "EARNINGS":       "#2ecc71",
    "PARTNERSHIP":    "#1abc9c",
    "REGULATORY":     "#e67e22",
    "LAYOFFS_HIRING": "#95a5a6",
    "RESEARCH_PAPER": "#3498db",
    "OTHER":          "#bdc3c7",
}


class MiroClient:
    def __init__(self):
        self.token = os.environ["MIRO_API_TOKEN"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_board(self, name: str, description: str = "") -> dict:
        r = httpx.post(f"{BASE_URL}/boards", headers=self.headers, json={
            "name": name,
            "description": description,
        })
        r.raise_for_status()
        return r.json()

    def create_frame(self, board_id: str, title: str, x: int, y: int, width: int = 900, height: int = 700) -> dict:
        r = httpx.post(f"{BASE_URL}/boards/{board_id}/frames", headers=self.headers, json={
            "data": {"title": title, "format": "custom", "type": "freeform"},
            "position": {"x": x, "y": y, "origin": "center"},
            "geometry": {"width": width, "height": height},
        })
        r.raise_for_status()
        return r.json()

    def create_sticky_note(self, board_id: str, content: str, x: int, y: int, color: str = "yellow") -> dict:
        r = httpx.post(f"{BASE_URL}/boards/{board_id}/sticky_notes", headers=self.headers, json={
            "data": {"content": content, "shape": "square"},
            "style": {"fillColor": color},
            "position": {"x": x, "y": y, "origin": "center"},
            "geometry": {"width": 200},
        })
        r.raise_for_status()
        return r.json()

    def create_card(self, board_id: str, title: str, description: str, x: int, y: int, color: str = "#2d9bf0") -> dict:
        r = httpx.post(f"{BASE_URL}/boards/{board_id}/cards", headers=self.headers, json={
            "data": {"title": title, "description": description},
            "style": {"cardTheme": color},
            "position": {"x": x, "y": y, "origin": "center"},
            "geometry": {"width": 260, "height": 80},
        })
        r.raise_for_status()
        return r.json()

    def get_board_url(self, board: dict) -> str:
        return board.get("viewLink", "")
