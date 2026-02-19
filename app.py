#!/usr/bin/env python3
"""
ROI Polygon Tool — Camera Archive Edition
Manages ROI polygons across multiple cameras with local persistence.
Data stored in ~/.roi_tool/
"""

import sys
import os
import json
import re
import ast
import io
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QComboBox, QStatusBar, QSizePolicy,
    QShortcut, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLineEdit, QInputDialog, QMenu,
    QScrollArea, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QKeySequence, QFont

from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Persistence paths
# ---------------------------------------------------------------------------

APP_DIR   = Path.home() / ".roi_tool"
IMG_DIR   = APP_DIR / "images"
DATA_FILE = APP_DIR / "cameras.json"


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2e2e50;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #22223b;
    color: #8888aa;
    border: 1px solid #2e2e50;
    border-bottom: none;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: bold;
    min-width: 130px;
}
QTabBar::tab:selected { background-color: #7c3aed; color: #ffffff; }
QTabBar::tab:hover:!selected { background-color: #2e2e50; color: #e0e0f0; }

QPushButton {
    background-color: #7c3aed;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
    min-height: 32px;
}
QPushButton:hover   { background-color: #8b5cf6; }
QPushButton:pressed { background-color: #6d28d9; }
QPushButton:disabled { background-color: #3a3a5c; color: #606080; }

QPushButton#secondary {
    background-color: #22223b;
    border: 1px solid #3a3a5c;
    color: #e0e0f0;
}
QPushButton#secondary:hover  { background-color: #2e2e50; }
QPushButton#secondary:pressed { background-color: #1a1a2e; }

QPushButton#danger { background-color: #b91c1c; }
QPushButton#danger:hover  { background-color: #dc2626; }
QPushButton#danger:pressed { background-color: #991b1b; }

QPushButton#success { background-color: #047857; }
QPushButton#success:hover  { background-color: #059669; }
QPushButton#success:pressed { background-color: #065f46; }

QPushButton#teal { background-color: #0d9488; color: #f0fdfa; }
QPushButton#teal:hover  { background-color: #0f766e; }

QPushButton#blue { background-color: #1d4ed8; }
QPushButton#blue:hover  { background-color: #2563eb; }

QTextEdit {
    background-color: #0f0f1e;
    border: 1px solid #2e2e50;
    border-radius: 6px;
    color: #00e5c0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #7c3aed;
}

QLineEdit {
    background-color: #22223b;
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e0e0f0;
    min-height: 30px;
}
QLineEdit:focus { border-color: #7c3aed; }

QLabel { color: #e0e0f0; }

QGroupBox {
    border: 1px solid #2e2e50;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    color: #8888aa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #8888aa;
}

QComboBox {
    background-color: #22223b;
    border: 1px solid #3a3a5c;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e0e0f0;
    min-height: 30px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #22223b;
    border: 1px solid #3a3a5c;
    selection-background-color: #7c3aed;
    color: #e0e0f0;
}

QStatusBar {
    background-color: #0f0f1e;
    color: #8888aa;
    border-top: 1px solid #2e2e50;
}

QSplitter::handle { background-color: #2e2e50; width: 2px; }

QCheckBox { color: #e0e0f0; spacing: 8px; font-size: 13px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #3a3a5c;
    border-radius: 4px;
    background-color: #22223b;
}
QCheckBox::indicator:hover  { border-color: #7c3aed; }
QCheckBox::indicator:checked { background-color: #7c3aed; border-color: #7c3aed; }

/* ---- Sidebar tree ---- */
QTreeWidget {
    background-color: #12122a;
    border: none;
    color: #e0e0f0;
    font-size: 13px;
    outline: 0;
    show-decoration-selected: 1;
}
QTreeWidget::item { padding: 6px 4px; border-radius: 4px; }
QTreeWidget::item:selected { background-color: #7c3aed; color: #ffffff; }
QTreeWidget::item:hover:!selected { background-color: #22223b; }
QTreeWidget::branch { background-color: #12122a; }

/* ---- Scroll bars ---- */
QScrollArea { border: none; background-color: transparent; }
QScrollBar:vertical {
    background-color: #12122a; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #3a3a5c; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #7c3aed; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# ---------------------------------------------------------------------------
# Storage layer
# ---------------------------------------------------------------------------

class StorageManager:
    """Manages the ~/.roi_tool/ directory and cameras.json file."""

    def __init__(self):
        APP_DIR.mkdir(exist_ok=True)
        IMG_DIR.mkdir(exist_ok=True)

    def load(self) -> dict:
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"version": 1, "cameras": []}

    def save(self, data: dict):
        """Atomic write — prevents corruption on crash mid-write."""
        tmp = DATA_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(DATA_FILE)

    def copy_image(self, src_path: str, cam_id: str) -> str:
        """Copy source image into IMG_DIR, return stored filename."""
        src = Path(src_path)
        ext = src.suffix.lower() or ".jpg"
        filename = f"{cam_id}{ext}"
        shutil.copy2(src, IMG_DIR / filename)
        return filename

    def image_path(self, filename: str) -> str:
        return str(IMG_DIR / filename)

    def delete_image(self, filename: str):
        path = IMG_DIR / filename
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass


class CameraStore:
    """In-memory model layer. All mutations auto-save via StorageManager."""

    def __init__(self, storage: StorageManager):
        self._storage = storage
        self._data = storage.load()

    # ---- cameras ----

    def cameras(self) -> list:
        return self._data["cameras"]

    def get_camera(self, cam_id: str) -> dict | None:
        return next((c for c in self._data["cameras"] if c["id"] == cam_id), None)

    def add_camera(self, name: str, image_src: str) -> dict:
        cam_id = "cam_" + uuid.uuid4().hex[:8]
        filename = self._storage.copy_image(image_src, cam_id)
        cam = {
            "id": cam_id,
            "name": name,
            "image_filename": filename,
            "added_at": datetime.now().isoformat(),
            "rois": [],
        }
        self._data["cameras"].append(cam)
        self._storage.save(self._data)
        return cam

    def rename_camera(self, cam_id: str, new_name: str):
        cam = self.get_camera(cam_id)
        if cam:
            cam["name"] = new_name
            self._storage.save(self._data)

    def delete_camera(self, cam_id: str):
        cam = self.get_camera(cam_id)
        if cam:
            self._storage.delete_image(cam["image_filename"])
            self._data["cameras"] = [c for c in self._data["cameras"] if c["id"] != cam_id]
            self._storage.save(self._data)

    # ---- ROIs ----

    def get_roi(self, cam_id: str, roi_id: str) -> dict | None:
        cam = self.get_camera(cam_id)
        if not cam:
            return None
        return next((r for r in cam["rois"] if r["id"] == roi_id), None)

    def add_roi(self, cam_id: str, name: str, points: list, closed: bool) -> dict:
        cam = self.get_camera(cam_id)
        if not cam:
            return None
        now = datetime.now().isoformat()
        roi = {
            "id": "roi_" + uuid.uuid4().hex[:8],
            "name": name,
            "points": [list(p) for p in points],
            "closed": closed,
            "created_at": now,
            "updated_at": now,
        }
        cam["rois"].append(roi)
        self._storage.save(self._data)
        return roi

    def update_roi(self, cam_id: str, roi_id: str, points: list, closed: bool, name: str = None):
        cam = self.get_camera(cam_id)
        if not cam:
            return
        roi = next((r for r in cam["rois"] if r["id"] == roi_id), None)
        if not roi:
            return
        roi["points"] = [list(p) for p in points]
        roi["closed"] = closed
        roi["updated_at"] = datetime.now().isoformat()
        if name is not None:
            roi["name"] = name
        self._storage.save(self._data)

    def rename_roi(self, cam_id: str, roi_id: str, new_name: str):
        cam = self.get_camera(cam_id)
        if not cam:
            return
        roi = next((r for r in cam["rois"] if r["id"] == roi_id), None)
        if roi:
            roi["name"] = new_name
            self._storage.save(self._data)

    def delete_roi(self, cam_id: str, roi_id: str):
        cam = self.get_camera(cam_id)
        if cam:
            cam["rois"] = [r for r in cam["rois"] if r["id"] != roi_id]
            self._storage.save(self._data)


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def parse_coordinates(text: str) -> list:
    text = text.strip()
    if not text:
        raise ValueError("No coordinates provided.")

    def _to_num(v):
        f = float(v)
        return int(f) if f == int(f) else f

    # Corner JSON: {"roi": {"tl":{x,y}, ...}} or bare {"tl":...}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            roi = data.get("roi", data)
            if all(k in roi for k in ("tl", "tr", "br", "bl")):
                return [
                    (_to_num(roi["tl"]["x"]), _to_num(roi["tl"]["y"])),
                    (_to_num(roi["tr"]["x"]), _to_num(roi["tr"]["y"])),
                    (_to_num(roi["br"]["x"]), _to_num(roi["br"]["y"])),
                    (_to_num(roi["bl"]["x"]), _to_num(roi["bl"]["y"])),
                ]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # JSON array: [[x,y], ...]
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) >= 2:
            if isinstance(data[0], (list, tuple)) and len(data[0]) == 2:
                return [(_to_num(p[0]), _to_num(p[1])) for p in data]
    except (json.JSONDecodeError, TypeError):
        pass

    # Python literal
    try:
        data = ast.literal_eval(text)
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            if isinstance(data[0], (list, tuple)) and len(data[0]) == 2:
                return [(_to_num(p[0]), _to_num(p[1])) for p in data]
    except (ValueError, SyntaxError):
        pass

    # Flat numbers
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if len(numbers) >= 4 and len(numbers) % 2 == 0:
        return [(_to_num(numbers[i]), _to_num(numbers[i + 1]))
                for i in range(0, len(numbers), 2)]

    raise ValueError(
        "Could not parse coordinates.\n\n"
        "Supported formats:\n"
        "  [[x1,y1], [x2,y2], ...]\n"
        "  [(x1,y1), (x2,y2), ...]\n"
        "  x1,y1 x2,y2 ...\n"
        "  x1,y1,x2,y2,..."
    )


def _is_normalized(points) -> bool:
    return all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in points)


def _assign_corners(points) -> dict:
    if len(points) != 4:
        raise ValueError("Corner JSON requires exactly 4 polygon points.")
    by_y = sorted(points, key=lambda p: p[1])
    tl, tr = sorted(by_y[:2], key=lambda p: p[0])
    bl, br = sorted(by_y[2:], key=lambda p: p[0])
    return {"tl": tl, "tr": tr, "br": br, "bl": bl}


# ---------------------------------------------------------------------------
# Image drawing helpers
# ---------------------------------------------------------------------------

POLY_FILL    = (0, 229, 192, 50)
POLY_OUTLINE = (0, 229, 192, 255)
PT_FIRST     = (255, 215, 0)
PT_NORMAL    = (255, 107, 53)
PT_RADIUS    = 6
LINE_WIDTH   = 2


def _draw_polygon_overlay(img, points, closed=True, line_width=LINE_WIDTH, pt_radius=PT_RADIUS):
    out = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if len(points) >= 3:
        draw.polygon(points, fill=POLY_FILL)
    if len(points) >= 2:
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=POLY_OUTLINE, width=line_width)
        if closed and len(points) >= 3:
            draw.line([points[-1], points[0]], fill=POLY_OUTLINE, width=line_width)
    r = pt_radius
    for i, pt in enumerate(points):
        color = PT_FIRST if i == 0 else PT_NORMAL
        draw.ellipse([pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r],
                     fill=color, outline=(255, 255, 255, 255), width=2)
    out = Image.alpha_composite(out, overlay)
    return out.convert("RGB")


def _pil_to_qpixmap(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    pix = QPixmap()
    pix.loadFromData(buf.read())
    return pix


# ---------------------------------------------------------------------------
# Drawing Canvas
# ---------------------------------------------------------------------------

class DrawingCanvas(QLabel):
    points_changed = pyqtSignal(list, bool)
    SNAP_RADIUS = 14

    def __init__(self):
        super().__init__()
        self.orig_image = None
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self.points = []
        self.closed = False
        self._hover = None
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()

    # -- public API --

    def load_image(self, path: str):
        self.orig_image = Image.open(path).convert("RGB")
        self.points = []
        self.closed = False
        self._hover = None
        self._render()
        self.points_changed.emit(self.points, self.closed)
        self.setStyleSheet("QLabel { background-color: #1a1a2e; border: 2px solid #2e2e50; }")

    def load_polygon(self, points: list, closed: bool):
        """Pre-load an existing polygon for editing."""
        self.points = [tuple(p) for p in points]
        self.closed = closed
        self._render()
        self.points_changed.emit(self.points, self.closed)

    def get_points(self):
        return list(self.points), self.closed

    def undo_last(self):
        if self.closed:
            self.closed = False
        elif self.points:
            self.points.pop()
        self._render()
        self.points_changed.emit(self.points, self.closed)

    def clear_all(self):
        self.points = []
        self.closed = False
        self._hover = None
        self._render()
        self.points_changed.emit(self.points, self.closed)

    def close_polygon(self):
        if len(self.points) >= 3 and not self.closed:
            self.closed = True
            self._hover = None
            self._render()
            self.points_changed.emit(self.points, self.closed)

    def save_image(self, path: str) -> bool:
        if not self.orig_image:
            return False
        _draw_polygon_overlay(self.orig_image, self.points, closed=self.closed,
                               line_width=3, pt_radius=8).save(path)
        return True

    # -- rendering --

    def _show_placeholder(self):
        self.setText(
            "Load an image to start drawing\n\n"
            "Left-click  →  place vertex\n"
            "Right-click →  remove last vertex\n"
            "Click near ① or press 'Close Polygon'  →  close shape"
        )
        self.setStyleSheet(
            "QLabel { background-color: #1a1a2e; border: 2px dashed #2e2e50;"
            " color: #8888aa; font-size: 13px; }"
        )

    def _render(self):
        if not self.orig_image:
            return
        lw, lh = self.width(), self.height()
        iw, ih = self.orig_image.size
        scale = min(lw / iw, lh / ih)
        self._scale = scale
        dw, dh = int(iw * scale), int(ih * scale)
        self._offset_x = (lw - dw) // 2
        self._offset_y = (lh - dh) // 2

        disp = self.orig_image.resize((dw, dh), Image.LANCZOS).convert("RGBA")
        overlay = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        spts = [(int(x * scale), int(y * scale)) for x, y in self.points]

        if len(spts) >= 3:
            draw.polygon(spts, fill=POLY_FILL)
        if len(spts) >= 2:
            for i in range(len(spts) - 1):
                draw.line([spts[i], spts[i+1]], fill=POLY_OUTLINE, width=LINE_WIDTH)
            if self.closed:
                draw.line([spts[-1], spts[0]], fill=POLY_OUTLINE, width=LINE_WIDTH)

        if self._hover and not self.closed and spts:
            hx = self._hover[0] - self._offset_x
            hy = self._hover[1] - self._offset_y
            x0, y0 = spts[-1]
            steps = max(abs(hx - x0), abs(hy - y0))
            if steps > 0:
                for s in range(0, steps, 8):
                    t = s / steps
                    draw.ellipse([int(x0+(hx-x0)*t)-1, int(y0+(hy-y0)*t)-1,
                                  int(x0+(hx-x0)*t)+1, int(y0+(hy-y0)*t)+1],
                                 fill=(0, 229, 192, 140))

        snap = self._is_near_first(self._hover) if self._hover else False
        r = PT_RADIUS
        for i, pt in enumerate(spts):
            if i == 0 and snap and not self.closed:
                color, cr = (255, 255, 0, 255), r + 3
            else:
                color, cr = (PT_FIRST if i == 0 else PT_NORMAL) + (255,), r
            draw.ellipse([pt[0]-cr, pt[1]-cr, pt[0]+cr, pt[1]+cr],
                         fill=color, outline=(255, 255, 255, 230), width=2)
            draw.text((pt[0]+cr+3, pt[1]-cr), str(i+1), fill=(255, 255, 255, 220))

        disp = Image.alpha_composite(disp, overlay).convert("RGB")
        self.setPixmap(_pil_to_qpixmap(disp))

    def _label_to_image(self, label_pos):
        if not self.orig_image or not self._scale:
            return None
        px = label_pos.x() - self._offset_x
        py = label_pos.y() - self._offset_y
        dw = int(self.orig_image.width * self._scale)
        dh = int(self.orig_image.height * self._scale)
        if px < 0 or py < 0 or px >= dw or py >= dh:
            return None
        iw, ih = self.orig_image.size
        return (max(0, min(iw-1, int(px/self._scale))),
                max(0, min(ih-1, int(py/self._scale))))

    def _is_near_first(self, pos) -> bool:
        if not self.points or not pos:
            return False
        fx = int(self.points[0][0] * self._scale) + self._offset_x
        fy = int(self.points[0][1] * self._scale) + self._offset_y
        dx, dy = pos[0]-fx, pos[1]-fy
        return (dx*dx + dy*dy)**0.5 < self.SNAP_RADIUS

    def mousePressEvent(self, event):
        if not self.orig_image or self.closed:
            return
        if event.button() == Qt.LeftButton:
            pos = (event.pos().x(), event.pos().y())
            if len(self.points) >= 3 and self._is_near_first(pos):
                self.close_polygon()
                return
            img_pos = self._label_to_image(event.pos())
            if img_pos:
                self.points.append(img_pos)
                self._render()
                self.points_changed.emit(self.points, self.closed)
        elif event.button() == Qt.RightButton:
            self.undo_last()

    def mouseMoveEvent(self, event):
        if self.orig_image and not self.closed:
            self._hover = (event.pos().x(), event.pos().y())
            if self.points:
                self._render()

    def leaveEvent(self, event):
        self._hover = None
        if self.orig_image and self.points:
            self._render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.orig_image:
            self._render()


# ---------------------------------------------------------------------------
# Visualize Canvas
# ---------------------------------------------------------------------------

class VisCanvas(QLabel):
    def __init__(self):
        super().__init__()
        self.orig_image = None
        self._points = []
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()

    def _show_placeholder(self):
        self.setText("Load an image and paste coordinates,\nthen click  Visualize ROI")
        self.setStyleSheet(
            "QLabel { background-color: #1a1a2e; border: 2px dashed #2e2e50;"
            " color: #8888aa; font-size: 13px; }"
        )

    def load_image(self, path: str):
        self.orig_image = Image.open(path).convert("RGB")
        self._points = []
        self._render()
        self.setStyleSheet("QLabel { background-color: #1a1a2e; border: 2px solid #2e2e50; }")

    def set_polygon(self, points):
        self._points = points
        self._render()

    def clear_polygon(self):
        self._points = []
        self._render()

    def save_image(self, path: str) -> bool:
        if not self.orig_image:
            return False
        _draw_polygon_overlay(self.orig_image, self._points, closed=True,
                               line_width=3, pt_radius=8).save(path)
        return True

    def _render(self):
        if not self.orig_image:
            return
        lw, lh = self.width(), self.height()
        iw, ih = self.orig_image.size
        scale = min(lw / iw, lh / ih)
        dw, dh = int(iw * scale), int(ih * scale)
        disp = self.orig_image.resize((dw, dh), Image.LANCZOS)
        if self._points:
            spts = [(int(x * scale), int(y * scale)) for x, y in self._points]
            disp = _draw_polygon_overlay(disp, spts, closed=True,
                                          line_width=LINE_WIDTH, pt_radius=PT_RADIUS)
        self.setPixmap(_pil_to_qpixmap(disp))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.orig_image:
            self._render()


# ---------------------------------------------------------------------------
# Draw ROI Tab
# ---------------------------------------------------------------------------

class DrawROITab(QWidget):

    FORMATS = [
        ("JSON Array",   "[[x, y], ...]"),
        ("Python List",  "[(x, y), ...]"),
        ("Space-sep",    "x,y x,y ..."),
        ("Flat CSV",     "x1,y1,x2,y2,..."),
        ("Corner JSON",  '{"tl":{x,y}, "tr":{x,y}, "br":{x,y}, "bl":{x,y}}'),
    ]

    def __init__(self):
        super().__init__()
        self._setup_ui()
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo_last)
        QShortcut(QKeySequence("Escape"), self, self.canvas.clear_all)

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # Canvas side
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)

        tbar = QHBoxLayout()
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        tbar.addWidget(self.load_btn)
        tbar.addStretch()
        hint = QLabel("Left-click: add point  ·  Right-click/Ctrl+Z: undo  ·  Click near ①: close")
        hint.setStyleSheet("color: #8888aa; font-size: 11px;")
        tbar.addWidget(hint)
        ll.addLayout(tbar)

        self.canvas = DrawingCanvas()
        self.canvas.points_changed.connect(self._on_points_changed)
        ll.addWidget(self.canvas)
        splitter.addWidget(left)

        # Controls side
        right = QWidget()
        right.setMinimumWidth(265)
        right.setMaximumWidth(305)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        info_box = QGroupBox("Image Info")
        il = QVBoxLayout(info_box)
        self.lbl_size   = QLabel("Size: —")
        self.lbl_pts    = QLabel("Points: 0")
        self.lbl_status = QLabel("Load an image to begin")
        for lb in (self.lbl_size, self.lbl_pts, self.lbl_status):
            lb.setStyleSheet("color: #8888aa; font-size: 12px;")
            il.addWidget(lb)
        rl.addWidget(info_box)

        ctrl_box = QGroupBox("Controls")
        cl = QVBoxLayout(ctrl_box)
        self.btn_close = QPushButton("Close Polygon")
        self.btn_close.setObjectName("success")
        self.btn_close.clicked.connect(self.canvas.close_polygon)
        self.btn_close.setEnabled(False)
        cl.addWidget(self.btn_close)

        row = QHBoxLayout()
        self.btn_undo = QPushButton("Undo (Ctrl+Z)")
        self.btn_undo.setObjectName("secondary")
        self.btn_undo.clicked.connect(self.canvas.undo_last)
        self.btn_undo.setEnabled(False)
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setObjectName("danger")
        self.btn_clear.clicked.connect(self.canvas.clear_all)
        self.btn_clear.setEnabled(False)
        row.addWidget(self.btn_undo)
        row.addWidget(self.btn_clear)
        cl.addLayout(row)
        rl.addWidget(ctrl_box)

        fmt_box = QGroupBox("Output Format")
        fl = QVBoxLayout(fmt_box)
        self.fmt_combo = QComboBox()
        for label, ex in self.FORMATS:
            self.fmt_combo.addItem(f"{label}  —  {ex}")
        self.fmt_combo.currentIndexChanged.connect(self._update_output)
        fl.addWidget(self.fmt_combo)

        self.chk_normalize = QCheckBox("Normalize  (x/width, y/height  →  0.0–1.0)")
        self.chk_normalize.stateChanged.connect(self._update_output)
        fl.addWidget(self.chk_normalize)
        rl.addWidget(fmt_box)

        out_box = QGroupBox("Coordinates")
        ol = QVBoxLayout(out_box)
        self.coord_out = QTextEdit()
        self.coord_out.setReadOnly(True)
        self.coord_out.setMinimumHeight(120)
        self.coord_out.setMaximumHeight(190)
        self.coord_out.setPlaceholderText("Coordinates appear here once you place points…")
        ol.addWidget(self.coord_out)

        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.setObjectName("blue")
        btn_copy.clicked.connect(self._copy_coords)
        ol.addWidget(btn_copy)
        rl.addWidget(out_box)

        exp_box = QGroupBox("Export")
        el = QVBoxLayout(exp_box)
        btn_save = QPushButton("Save Image with ROI overlay")
        btn_save.setObjectName("secondary")
        btn_save.clicked.connect(self._save_image)
        el.addWidget(btn_save)
        rl.addWidget(exp_box)

        rl.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([720, 280])
        root.addWidget(splitter)

    # -- public API for ROIEditorPanel --

    def load_image_from_path(self, path: str):
        if not path or not os.path.exists(path):
            return
        self.canvas.load_image(path)
        w, h = self.canvas.orig_image.size
        self.lbl_size.setText(f"Size: {w} × {h} px")
        self.lbl_status.setText("Click on the image to place polygon vertices")

    def load_polygon(self, points: list, closed: bool):
        self.canvas.load_polygon(points, closed)

    def get_points(self):
        return self.canvas.get_points()

    # -- slots --

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*)"
        )
        if path:
            self.load_image_from_path(path)

    def _on_points_changed(self, points, closed):
        n = len(points)
        self.lbl_pts.setText(f"Points: {n}")
        self.btn_undo.setEnabled(n > 0 or closed)
        self.btn_clear.setEnabled(n > 0)
        self.btn_close.setEnabled(n >= 3 and not closed)
        if closed:
            self.lbl_status.setText(f"Polygon closed  ({n} vertices)")
        elif n == 0:
            self.lbl_status.setText("Click on the image to place polygon vertices")
        elif n < 3:
            self.lbl_status.setText(f"Need {3-n} more point(s) to close polygon")
        else:
            self.lbl_status.setText("Click near ① or press 'Close Polygon'")
        self._update_output()

    def _update_output(self):
        raw = self.canvas.points
        if not raw:
            self.coord_out.setPlainText("")
            return

        normalize = self.chk_normalize.isChecked()
        if normalize and self.canvas.orig_image:
            iw, ih = self.canvas.orig_image.size
            points = [(x / iw, y / ih) for x, y in raw]
            fmt_val = lambda v: f"{v:.6f}"
            num_val = lambda v: round(v, 6)
        else:
            points = raw
            fmt_val = lambda v: str(v)
            num_val = lambda v: v

        idx = self.fmt_combo.currentIndex()
        if idx == 0:
            text = "[\n" + ",\n".join(f"  [{fmt_val(x)}, {fmt_val(y)}]" for x, y in points) + "\n]"
        elif idx == 1:
            text = "[\n" + ",\n".join(f"  ({fmt_val(x)}, {fmt_val(y)})" for x, y in points) + "\n]"
        elif idx == 2:
            text = "  ".join(f"{fmt_val(x)},{fmt_val(y)}" for x, y in points)
        elif idx == 3:
            text = ", ".join(fmt_val(v) for x, y in points for v in (x, y))
        else:  # Corner JSON
            if len(points) != 4:
                text = (f"# Corner JSON requires exactly 4 points.\n"
                        f"# Currently {len(points)} point(s) placed.")
            else:
                c = _assign_corners(points)
                text = json.dumps(
                    {"roi": {k: {"x": num_val(c[k][0]), "y": num_val(c[k][1])}
                             for k in ("tl", "tr", "br", "bl")}},
                    indent=4)
        self.coord_out.setPlainText(text)

    def _copy_coords(self):
        text = self.coord_out.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_image(self):
        if not self.canvas.orig_image:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png);;JPEG (*.jpg)")
        if path and self.canvas.save_image(path):
            QMessageBox.information(self, "Saved", f"Image saved:\n{path}")


# ---------------------------------------------------------------------------
# Visualize ROI Tab
# ---------------------------------------------------------------------------

class VisualizeROITab(QWidget):

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)

        tbar = QHBoxLayout()
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        tbar.addWidget(self.load_btn)
        tbar.addStretch()
        self.lbl_img = QLabel("No image loaded")
        self.lbl_img.setStyleSheet("color: #8888aa; font-size: 11px;")
        tbar.addWidget(self.lbl_img)
        ll.addLayout(tbar)

        self.canvas = VisCanvas()
        ll.addWidget(self.canvas)
        splitter.addWidget(left)

        right = QWidget()
        right.setMinimumWidth(265)
        right.setMaximumWidth(305)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        cin_box = QGroupBox("Paste Coordinates")
        cl = QVBoxLayout(cin_box)
        hint = QLabel("Formats: [[x,y],...] · [(x,y),...] · x,y x,y · x1,y1,x2,y2 · Corner JSON")
        hint.setStyleSheet("color: #8888aa; font-size: 11px;")
        hint.setWordWrap(True)
        cl.addWidget(hint)

        self.coord_in = QTextEdit()
        self.coord_in.setMinimumHeight(120)
        self.coord_in.setMaximumHeight(190)
        self.coord_in.setPlaceholderText("Paste your coordinates here…")
        cl.addWidget(self.coord_in)

        self.chk_normalized = QCheckBox("Normalized coords  (0.0–1.0  →  scale to image)")
        cl.addWidget(self.chk_normalized)
        rl.addWidget(cin_box)

        btn_vis = QPushButton("Visualize ROI")
        btn_vis.setStyleSheet(
            "QPushButton { background-color: #0d9488; color: #f0fdfa;"
            " font-size: 14px; padding: 10px; }"
            "QPushButton:hover { background-color: #0f766e; }"
        )
        btn_vis.clicked.connect(self._visualize)
        rl.addWidget(btn_vis)

        btn_clear = QPushButton("Clear ROI")
        btn_clear.setObjectName("secondary")
        btn_clear.clicked.connect(self._clear_roi)
        rl.addWidget(btn_clear)

        info_box = QGroupBox("ROI Info")
        il = QVBoxLayout(info_box)
        self.lbl_status = QLabel("No ROI loaded")
        self.lbl_status.setStyleSheet("color: #8888aa; font-size: 12px;")
        self.lbl_pts = QLabel("")
        self.lbl_pts.setStyleSheet("color: #8888aa; font-size: 11px;")
        self.lbl_pts.setWordWrap(True)
        il.addWidget(self.lbl_status)
        il.addWidget(self.lbl_pts)
        rl.addWidget(info_box)

        exp_box = QGroupBox("Export")
        el = QVBoxLayout(exp_box)
        btn_save = QPushButton("Save Image with ROI overlay")
        btn_save.setObjectName("secondary")
        btn_save.clicked.connect(self._save_image)
        el.addWidget(btn_save)
        rl.addWidget(exp_box)

        rl.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([720, 280])
        root.addWidget(splitter)

    # -- public API for ROIEditorPanel --

    def load_image_from_path(self, path: str):
        if not path or not os.path.exists(path):
            return
        self.canvas.load_image(path)
        w, h = self.canvas.orig_image.size
        self.lbl_img.setText(f"{w} × {h} px")

    def show_polygon(self, points: list):
        pts = [(int(x), int(y)) for x, y in points]
        self.canvas.set_polygon(pts)
        self.lbl_status.setText(f"ROI visualized  ({len(pts)} vertices)")
        preview = "  ".join(f"({x},{y})" for x, y in pts[:6])
        if len(pts) > 6:
            preview += f"  … +{len(pts)-6} more"
        self.lbl_pts.setText(preview)

    # -- slots --

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*)"
        )
        if path:
            self.load_image_from_path(path)

    def _visualize(self):
        if not self.canvas.orig_image:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        text = self.coord_in.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Coordinates", "Please paste coordinates first.")
            return
        try:
            parsed = parse_coordinates(text)
            if len(parsed) < 2:
                raise ValueError("At least 2 points required.")
            if self.chk_normalized.isChecked():
                if not _is_normalized(parsed):
                    raise ValueError(
                        "Some values are outside [0.0, 1.0].\n"
                        "Uncheck 'Normalized' for pixel coordinates."
                    )
                iw, ih = self.canvas.orig_image.size
                points = [(int(round(x*iw)), int(round(y*ih))) for x, y in parsed]
            else:
                points = [(int(round(x)), int(round(y))) for x, y in parsed]
            self.show_polygon(points)
        except ValueError as exc:
            QMessageBox.critical(self, "Parse Error", str(exc))

    def _clear_roi(self):
        self.canvas.clear_polygon()
        self.lbl_status.setText("No ROI loaded")
        self.lbl_pts.setText("")

    def _save_image(self):
        if not self.canvas.orig_image:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png);;JPEG (*.jpg)")
        if path and self.canvas.save_image(path):
            QMessageBox.information(self, "Saved", f"Image saved:\n{path}")


# ---------------------------------------------------------------------------
# Sidebar Panel
# ---------------------------------------------------------------------------

class SidebarPanel(QWidget):
    camera_selected         = pyqtSignal(str)
    roi_selected            = pyqtSignal(str, str)
    add_camera_requested    = pyqtSignal()
    add_roi_requested       = pyqtSignal(str)
    rename_camera_requested = pyqtSignal(str)
    rename_roi_requested    = pyqtSignal(str, str)
    delete_camera_requested = pyqtSignal(str)
    delete_roi_requested    = pyqtSignal(str, str)

    _CAM_ROLE = Qt.UserRole
    _ROI_ROLE = Qt.UserRole + 1

    def __init__(self):
        super().__init__()
        self.setFixedWidth(235)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QLabel("  CAMERAS")
        header.setFixedHeight(38)
        header.setStyleSheet(
            "background-color: #0f0f1e; color: #7c3aed; font-weight: bold;"
            " font-size: 11px; padding-left: 12px; letter-spacing: 1px;"
            " border-bottom: 1px solid #2e2e50;"
        )
        lay.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.tree)

        add_btn = QPushButton("＋  Add Camera")
        add_btn.setFixedHeight(42)
        add_btn.setStyleSheet(
            "QPushButton { border: none; border-top: 1px solid #2e2e50; border-radius: 0;"
            " background-color: #0f0f1e; color: #7c3aed; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #1a1a3e; }"
        )
        add_btn.clicked.connect(self.add_camera_requested)
        lay.addWidget(add_btn)

    def refresh(self, cameras: list):
        # Save expanded state
        expanded = set()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.isExpanded():
                expanded.add(item.data(0, self._CAM_ROLE))

        # Save selection
        sel = self.tree.currentItem()
        sel_cam = sel.data(0, self._CAM_ROLE) if sel else None
        sel_roi = sel.data(0, self._ROI_ROLE) if sel else None

        self.tree.clear()

        for cam in cameras:
            cam_item = QTreeWidgetItem([cam["name"]])
            cam_item.setData(0, self._CAM_ROLE, cam["id"])
            cam_item.setData(0, self._ROI_ROLE, None)
            cam_item.setToolTip(0, cam["name"])
            f = cam_item.font(0)
            f.setBold(True)
            cam_item.setFont(0, f)
            self.tree.addTopLevelItem(cam_item)

            for roi in cam["rois"]:
                roi_item = QTreeWidgetItem([f"    {roi['name']}"])
                roi_item.setData(0, self._CAM_ROLE, cam["id"])
                roi_item.setData(0, self._ROI_ROLE, roi["id"])
                roi_item.setToolTip(0, roi["name"])
                cam_item.addChild(roi_item)

            if cam["id"] in expanded:
                cam_item.setExpanded(True)

            # Restore selection
            if sel_cam == cam["id"]:
                if sel_roi is None:
                    self.tree.setCurrentItem(cam_item)
                else:
                    for j in range(cam_item.childCount()):
                        child = cam_item.child(j)
                        if child.data(0, self._ROI_ROLE) == sel_roi:
                            self.tree.setCurrentItem(child)
                            break

    def select_camera(self, cam_id: str):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, self._CAM_ROLE) == cam_id:
                self.tree.setCurrentItem(item)
                item.setExpanded(True)
                return

    def select_roi(self, cam_id: str, roi_id: str):
        for i in range(self.tree.topLevelItemCount()):
            cam_item = self.tree.topLevelItem(i)
            if cam_item.data(0, self._CAM_ROLE) == cam_id:
                cam_item.setExpanded(True)
                for j in range(cam_item.childCount()):
                    roi_item = cam_item.child(j)
                    if roi_item.data(0, self._ROI_ROLE) == roi_id:
                        self.tree.setCurrentItem(roi_item)
                        return

    def _on_item_clicked(self, item, _col):
        cam_id = item.data(0, self._CAM_ROLE)
        roi_id = item.data(0, self._ROI_ROLE)
        if roi_id:
            self.roi_selected.emit(cam_id, roi_id)
        elif cam_id:
            self.camera_selected.emit(cam_id)

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        cam_id = item.data(0, self._CAM_ROLE)
        roi_id = item.data(0, self._ROI_ROLE)
        menu = QMenu(self)
        if roi_id:
            menu.addAction("Rename ROI").triggered.connect(
                lambda: self.rename_roi_requested.emit(cam_id, roi_id))
            menu.addSeparator()
            a = menu.addAction("Delete ROI")
            a.triggered.connect(lambda: self.delete_roi_requested.emit(cam_id, roi_id))
        elif cam_id:
            menu.addAction("Add ROI").triggered.connect(
                lambda: self.add_roi_requested.emit(cam_id))
            menu.addAction("Rename Camera").triggered.connect(
                lambda: self.rename_camera_requested.emit(cam_id))
            menu.addSeparator()
            a = menu.addAction("Delete Camera")
            a.triggered.connect(lambda: self.delete_camera_requested.emit(cam_id))
        if not menu.isEmpty():
            menu.exec_(self.tree.viewport().mapToGlobal(pos))


# ---------------------------------------------------------------------------
# Welcome Panel
# ---------------------------------------------------------------------------

class WelcomePanel(QWidget):
    add_camera_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(12)

        icon = QLabel("🎥")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 56px;")
        lay.addWidget(icon)

        title = QLabel("No cameras in your inventory")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0f0;")
        lay.addWidget(title)

        sub = QLabel("Add your first camera to start managing ROI polygons.\nAll data is stored locally and persists between sessions.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #8888aa; font-size: 13px;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        btn = QPushButton("＋  Add Camera")
        btn.setFixedWidth(200)
        btn.clicked.connect(self.add_camera_requested)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn)
        row.addStretch()
        lay.addLayout(row)


# ---------------------------------------------------------------------------
# Camera Detail Panel
# ---------------------------------------------------------------------------

class CameraDetailPanel(QWidget):
    add_roi_requested  = pyqtSignal()
    roi_open_requested = pyqtSignal(str)   # roi_id

    def __init__(self):
        super().__init__()
        self._cam = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        # Title row
        hdr = QHBoxLayout()
        self.lbl_name = QLabel("Camera")
        self.lbl_name.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0f0;")
        hdr.addWidget(self.lbl_name)
        hdr.addStretch()
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color: #8888aa; font-size: 11px;")
        hdr.addWidget(self.lbl_meta)
        root.addLayout(hdr)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("QFrame { color: #2e2e50; }")
        root.addWidget(line)

        body = QHBoxLayout()
        body.setSpacing(28)

        # Thumbnail
        self.thumb = QLabel("No image")
        self.thumb.setFixedSize(300, 210)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet(
            "background-color: #12122a; border: 1px solid #2e2e50;"
            " border-radius: 8px; color: #8888aa;"
        )
        body.addWidget(self.thumb, 0, Qt.AlignTop)

        # ROI list
        roi_panel = QWidget()
        rl = QVBoxLayout(roi_panel)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        roi_hdr = QHBoxLayout()
        roi_title = QLabel("ROI Polygons")
        roi_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0e0f0;")
        roi_hdr.addWidget(roi_title)
        roi_hdr.addStretch()
        add_btn = QPushButton("＋ Add ROI")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self.add_roi_requested)
        roi_hdr.addWidget(add_btn)
        rl.addLayout(roi_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.roi_container = QWidget()
        self.roi_layout = QVBoxLayout(self.roi_container)
        self.roi_layout.setContentsMargins(0, 0, 4, 0)
        self.roi_layout.setSpacing(8)
        self.roi_layout.addStretch()
        scroll.setWidget(self.roi_container)
        rl.addWidget(scroll)

        body.addWidget(roi_panel)
        root.addLayout(body)

    def load_camera(self, cam: dict, image_path: str):
        self._cam = cam
        self.lbl_name.setText(cam["name"])
        added = cam.get("added_at", "")[:10]
        n = len(cam["rois"])
        self.lbl_meta.setText(f"Added {added}  ·  {n} ROI(s)")

        # Thumbnail
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path).convert("RGB")
                img.thumbnail((300, 210), Image.LANCZOS)
                self.thumb.setPixmap(_pil_to_qpixmap(img))
                self.thumb.setText("")
            except Exception:
                self.thumb.setText("Could not load image")
        else:
            self.thumb.setText("Image file not found")

        self._rebuild_roi_list()

    def _rebuild_roi_list(self):
        while self.roi_layout.count() > 1:
            item = self.roi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._cam or not self._cam["rois"]:
            empty = QLabel("No ROIs yet.  Click '＋ Add ROI' to create one.")
            empty.setStyleSheet("color: #8888aa; font-size: 12px; padding: 12px 0;")
            self.roi_layout.insertWidget(0, empty)
            return

        for roi in reversed(self._cam["rois"]):
            self.roi_layout.insertWidget(0, self._make_card(roi))

    def _make_card(self, roi: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #22223b; border: 1px solid #2e2e50;"
            " border-radius: 8px; }"
            "QFrame:hover { border-color: #7c3aed; }"
        )
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)

        info = QVBoxLayout()
        name_lbl = QLabel(roi["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #e0e0f0;")
        info.addWidget(name_lbl)

        pts = roi.get("points", [])
        ts = roi.get("updated_at", roi.get("created_at", ""))[:16].replace("T", "  ")
        meta = QLabel(f"{len(pts)} vertices  ·  last saved  {ts}")
        meta.setStyleSheet("color: #8888aa; font-size: 11px;")
        info.addWidget(meta)

        lay.addLayout(info)
        lay.addStretch()

        btn = QPushButton("Open")
        btn.setFixedWidth(72)
        roi_id = roi["id"]
        btn.clicked.connect(lambda: self.roi_open_requested.emit(roi_id))
        lay.addWidget(btn)
        return card


# ---------------------------------------------------------------------------
# ROI Editor Panel  (wraps DrawROITab + VisualizeROITab)
# ---------------------------------------------------------------------------

class ROIEditorPanel(QWidget):
    # cam_id, roi_id ("" = new), points, closed, name
    roi_saved = pyqtSignal(str, str, list, bool, str)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cam_id = ""
        self._roi_id = ""
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Header bar ----
        hdr = QWidget()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(
            "background-color: #0f0f1e; border-bottom: 1px solid #2e2e50;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)

        back = QPushButton("← Back")
        back.setObjectName("secondary")
        back.setFixedWidth(80)
        back.clicked.connect(self.cancelled)
        hl.addWidget(back)

        self.lbl_crumb = QLabel()
        self.lbl_crumb.setStyleSheet("color: #8888aa; font-size: 12px;")
        hl.addWidget(self.lbl_crumb)

        hl.addStretch()

        hl.addWidget(QLabel("ROI name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter ROI name…")
        self.name_edit.setFixedWidth(210)
        hl.addWidget(self.name_edit)

        self.save_btn = QPushButton("💾  Save ROI")
        self.save_btn.setObjectName("success")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._on_save)
        hl.addWidget(self.save_btn)

        root.addWidget(hdr)

        # ---- Tabs ----
        self.tabs = QTabWidget()
        self.draw_tab = DrawROITab()
        self.vis_tab  = VisualizeROITab()
        self.tabs.addTab(self.draw_tab, "  ✏  Draw / Edit  ")
        self.tabs.addTab(self.vis_tab,  "  👁  Visualize / Export  ")
        root.addWidget(self.tabs)

    def load_for_new(self, cam: dict, image_path: str):
        self._cam_id = cam["id"]
        self._roi_id = ""
        self.lbl_crumb.setText(f"{cam['name']}  ›  New ROI")
        self.name_edit.setText("New ROI")
        self.name_edit.selectAll()
        self.draw_tab.load_image_from_path(image_path)
        self.draw_tab.canvas.clear_all()
        self.tabs.setCurrentIndex(0)
        self.name_edit.setFocus()

    def load_for_edit(self, cam: dict, roi: dict, image_path: str):
        self._cam_id = cam["id"]
        self._roi_id = roi["id"]
        self.lbl_crumb.setText(f"{cam['name']}  ›  {roi['name']}")
        self.name_edit.setText(roi["name"])
        pts = roi.get("points", [])
        closed = roi.get("closed", True)
        self.draw_tab.load_image_from_path(image_path)
        self.draw_tab.load_polygon(pts, closed)
        self.vis_tab.load_image_from_path(image_path)
        if pts:
            self.vis_tab.show_polygon(pts)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a name for this ROI.")
            self.name_edit.setFocus()
            return

        points, closed = self.draw_tab.get_points()

        if len(points) < 3:
            QMessageBox.warning(self, "Not Enough Points",
                                "Place at least 3 vertices before saving.")
            self.tabs.setCurrentIndex(0)
            return

        if not closed:
            resp = QMessageBox.question(
                self, "Polygon Not Closed",
                "The polygon is not closed. Close it automatically before saving?",
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes,
            )
            if resp == QMessageBox.Yes:
                closed = True
            else:
                return

        self.roi_saved.emit(self._cam_id, self._roi_id, points, closed, name)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._storage = StorageManager()
        self._store   = CameraStore(self._storage)
        self._current_cam_id = None

        self.setWindowTitle("ROI Polygon Tool — Camera Archive")
        self.setMinimumSize(1020, 660)
        self.resize(1300, 800)

        self._setup_ui()
        self._wire_signals()
        self._refresh_sidebar()
        self._show_initial()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self.sidebar = SidebarPanel()
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.welcome_panel = WelcomePanel()
        self.camera_panel  = CameraDetailPanel()
        self.roi_panel     = ROIEditorPanel()
        self.stack.addWidget(self.welcome_panel)  # 0
        self.stack.addWidget(self.camera_panel)   # 1
        self.stack.addWidget(self.roi_panel)      # 2
        splitter.addWidget(self.stack)

        splitter.setSizes([235, 1065])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self.sb = QStatusBar()
        self.sb.showMessage("Select a camera from the sidebar, or click '＋ Add Camera'.")
        self.setStatusBar(self.sb)

    def _wire_signals(self):
        s = self.sidebar
        s.add_camera_requested.connect(self._on_add_camera)
        s.camera_selected.connect(self._on_camera_selected)
        s.roi_selected.connect(self._on_roi_selected)
        s.add_roi_requested.connect(self._on_add_roi)
        s.rename_camera_requested.connect(self._on_rename_camera)
        s.rename_roi_requested.connect(self._on_rename_roi)
        s.delete_camera_requested.connect(self._on_delete_camera)
        s.delete_roi_requested.connect(self._on_delete_roi)

        self.welcome_panel.add_camera_requested.connect(self._on_add_camera)
        self.camera_panel.add_roi_requested.connect(
            lambda: self._on_add_roi(self._current_cam_id) if self._current_cam_id else None)
        self.camera_panel.roi_open_requested.connect(self._on_roi_open_from_panel)
        self.roi_panel.roi_saved.connect(self._on_roi_saved)
        self.roi_panel.cancelled.connect(self._on_editor_cancelled)

    def _refresh_sidebar(self):
        self.sidebar.refresh(self._store.cameras())

    def _show_initial(self):
        cams = self._store.cameras()
        if cams:
            self._current_cam_id = cams[0]["id"]
            self.sidebar.select_camera(cams[0]["id"])
            self._show_camera(cams[0])
        else:
            self.stack.setCurrentIndex(0)

    # ---- camera actions ----

    def _on_add_camera(self):
        name, ok = QInputDialog.getText(self, "Add Camera", "Camera name:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Camera Reference Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*)"
        )
        if not path:
            return
        try:
            cam = self._store.add_camera(name.strip(), path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not add camera:\n{exc}")
            return
        self._current_cam_id = cam["id"]
        self._refresh_sidebar()
        self.sidebar.select_camera(cam["id"])
        self._show_camera(cam)
        self.sb.showMessage(f"Camera '{cam['name']}' added.")

    def _on_camera_selected(self, cam_id: str):
        cam = self._store.get_camera(cam_id)
        if cam:
            self._current_cam_id = cam_id
            self._show_camera(cam)

    def _show_camera(self, cam: dict):
        img_path = self._storage.image_path(cam["image_filename"])
        self.camera_panel.load_camera(cam, img_path)
        self.stack.setCurrentIndex(1)
        self.sb.showMessage(f"Camera: {cam['name']}  ·  {len(cam['rois'])} ROI(s)")

    def _on_rename_camera(self, cam_id: str):
        cam = self._store.get_camera(cam_id)
        if not cam:
            return
        name, ok = QInputDialog.getText(self, "Rename Camera", "New name:", text=cam["name"])
        if ok and name.strip():
            self._store.rename_camera(cam_id, name.strip())
            self._refresh_sidebar()
            if self._current_cam_id == cam_id:
                self._show_camera(self._store.get_camera(cam_id))
            self.sb.showMessage(f"Camera renamed to '{name.strip()}'.")

    def _on_delete_camera(self, cam_id: str):
        cam = self._store.get_camera(cam_id)
        if not cam:
            return
        resp = QMessageBox.question(
            self, "Delete Camera",
            f"Delete '{cam['name']}' and all {len(cam['rois'])} ROI(s)?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        if resp != QMessageBox.Yes:
            return
        self._store.delete_camera(cam_id)
        if self._current_cam_id == cam_id:
            self._current_cam_id = None
        self._refresh_sidebar()
        self._show_initial()
        self.sb.showMessage("Camera deleted.")

    # ---- ROI actions ----

    def _on_add_roi(self, cam_id: str):
        if not cam_id:
            return
        cam = self._store.get_camera(cam_id)
        if not cam:
            return
        self._current_cam_id = cam_id
        img_path = self._storage.image_path(cam["image_filename"])
        self.roi_panel.load_for_new(cam, img_path)
        self.stack.setCurrentIndex(2)
        self.sb.showMessage(f"Drawing new ROI for camera '{cam['name']}'…")

    def _on_roi_selected(self, cam_id: str, roi_id: str):
        cam = self._store.get_camera(cam_id)
        roi = self._store.get_roi(cam_id, roi_id)
        if cam and roi:
            self._current_cam_id = cam_id
            img_path = self._storage.image_path(cam["image_filename"])
            self.roi_panel.load_for_edit(cam, roi, img_path)
            self.stack.setCurrentIndex(2)
            self.sb.showMessage(f"{cam['name']}  ›  {roi['name']}  ({len(roi['points'])} vertices)")

    def _on_roi_open_from_panel(self, roi_id: str):
        if not self._current_cam_id:
            return
        self._on_roi_selected(self._current_cam_id, roi_id)
        self.sidebar.select_roi(self._current_cam_id, roi_id)

    def _on_roi_saved(self, cam_id: str, roi_id: str, points: list, closed: bool, name: str):
        if roi_id == "":
            roi = self._store.add_roi(cam_id, name, points, closed)
            roi_id = roi["id"]
            self.sb.showMessage(f"ROI '{name}' saved.")
        else:
            self._store.update_roi(cam_id, roi_id, points, closed, name)
            self.sb.showMessage(f"ROI '{name}' updated.")

        self._refresh_sidebar()
        self.sidebar.select_roi(cam_id, roi_id)

        cam = self._store.get_camera(cam_id)
        roi = self._store.get_roi(cam_id, roi_id)
        if cam and roi:
            img_path = self._storage.image_path(cam["image_filename"])
            self.roi_panel.load_for_edit(cam, roi, img_path)

    def _on_rename_roi(self, cam_id: str, roi_id: str):
        roi = self._store.get_roi(cam_id, roi_id)
        if not roi:
            return
        name, ok = QInputDialog.getText(self, "Rename ROI", "New name:", text=roi["name"])
        if ok and name.strip():
            self._store.rename_roi(cam_id, roi_id, name.strip())
            self._refresh_sidebar()
            self.sb.showMessage(f"ROI renamed to '{name.strip()}'.")

    def _on_delete_roi(self, cam_id: str, roi_id: str):
        roi = self._store.get_roi(cam_id, roi_id)
        if not roi:
            return
        resp = QMessageBox.question(
            self, "Delete ROI",
            f"Delete ROI '{roi['name']}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel,
        )
        if resp != QMessageBox.Yes:
            return
        self._store.delete_roi(cam_id, roi_id)
        self._refresh_sidebar()
        cam = self._store.get_camera(cam_id)
        if cam:
            self._show_camera(cam)
        self.sb.showMessage("ROI deleted.")

    def _on_editor_cancelled(self):
        if self._current_cam_id:
            cam = self._store.get_camera(self._current_cam_id)
            if cam:
                self.sidebar.select_camera(self._current_cam_id)
                self._show_camera(cam)
                return
        self.stack.setCurrentIndex(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ROI Polygon Tool")
    app.setStyleSheet(STYLESHEET)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
