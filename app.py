#!/usr/bin/env python3
"""
ROI Polygon Drawer & Visualizer
A desktop tool for drawing and visualizing Region of Interest polygons on images.

Usage:
    python app.py
"""

import sys
import json
import re
import ast
import io

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QComboBox, QStatusBar, QSizePolicy,
    QShortcut, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QKeySequence

from PIL import Image, ImageDraw


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
    padding: 10px 28px;
    font-size: 13px;
    font-weight: bold;
    min-width: 140px;
}

QTabBar::tab:selected {
    background-color: #7c3aed;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #2e2e50;
    color: #e0e0f0;
}

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

QPushButton:hover  { background-color: #8b5cf6; }
QPushButton:pressed { background-color: #6d28d9; }
QPushButton:disabled { background-color: #3a3a5c; color: #606080; }

QPushButton#secondary {
    background-color: #22223b;
    border: 1px solid #3a3a5c;
    color: #e0e0f0;
}
QPushButton#secondary:hover  { background-color: #2e2e50; }
QPushButton#secondary:pressed { background-color: #1a1a2e; }

QPushButton#danger {
    background-color: #b91c1c;
}
QPushButton#danger:hover  { background-color: #dc2626; }
QPushButton#danger:pressed { background-color: #991b1b; }

QPushButton#success {
    background-color: #047857;
}
QPushButton#success:hover  { background-color: #059669; }
QPushButton#success:pressed { background-color: #065f46; }

QPushButton#teal {
    background-color: #0d9488;
    color: #f0fdfa;
}
QPushButton#teal:hover  { background-color: #0f766e; }
QPushButton#teal:pressed { background-color: #0d7a6e; }

QPushButton#blue {
    background-color: #1d4ed8;
}
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

QSplitter::handle {
    background-color: #2e2e50;
    width: 3px;
}

QCheckBox {
    color: #e0e0f0;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #3a3a5c;
    border-radius: 4px;
    background-color: #22223b;
}
QCheckBox::indicator:hover {
    border-color: #7c3aed;
}
QCheckBox::indicator:checked {
    background-color: #7c3aed;
    border-color: #7c3aed;
}
"""


# ---------------------------------------------------------------------------
# Coordinate parser
# ---------------------------------------------------------------------------

def parse_coordinates(text: str) -> list[tuple[float, float]]:
    """
    Parse polygon coordinates from various text formats:
      - [[x1,y1], [x2,y2], ...]     JSON / Python nested list
      - [(x1,y1), (x2,y2), ...]     Python list of tuples
      - x1,y1 x2,y2 ...             Space-separated pairs
      - x1,y1,x2,y2,...             Flat CSV

    Floats are preserved so callers can detect normalized (0–1) coords.
    Raises ValueError if parsing fails.
    """
    text = text.strip()
    if not text:
        raise ValueError("No coordinates provided.")

    def _to_num(v):
        f = float(v)
        return int(f) if f == int(f) else f

    # 1a) Try Corner JSON: {"roi": {"tl":{x,y}, "tr":{x,y}, "br":{x,y}, "bl":{x,y}}}
    #     Also accepts the dict without the "roi" wrapper.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            roi = data.get("roi", data)   # unwrap "roi" key if present
            if all(k in roi for k in ("tl", "tr", "br", "bl")):
                return [
                    (_to_num(roi["tl"]["x"]), _to_num(roi["tl"]["y"])),
                    (_to_num(roi["tr"]["x"]), _to_num(roi["tr"]["y"])),
                    (_to_num(roi["br"]["x"]), _to_num(roi["br"]["y"])),
                    (_to_num(roi["bl"]["x"]), _to_num(roi["bl"]["y"])),
                ]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # 1b) Try JSON: [[x,y], ...]
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) >= 2:
            first = data[0]
            if isinstance(first, (list, tuple)) and len(first) == 2:
                return [(_to_num(p[0]), _to_num(p[1])) for p in data]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # 2) Try Python literal: [(x,y), ...] or [[x,y], ...]
    try:
        data = ast.literal_eval(text)
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            first = data[0]
            if isinstance(first, (list, tuple)) and len(first) == 2:
                return [(_to_num(p[0]), _to_num(p[1])) for p in data]
    except (ValueError, SyntaxError):
        pass

    # 3) Extract all numbers and pair them up
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if len(numbers) >= 4 and len(numbers) % 2 == 0:
        points = []
        for i in range(0, len(numbers), 2):
            points.append((_to_num(numbers[i]), _to_num(numbers[i + 1])))
        return points

    raise ValueError(
        "Could not parse coordinates.\n\n"
        "Supported formats:\n"
        "  [[x1,y1], [x2,y2], ...]\n"
        "  [(x1,y1), (x2,y2), ...]\n"
        "  x1,y1 x2,y2 ...\n"
        "  x1,y1,x2,y2,..."
    )


def _is_normalized(points: list[tuple[float, float]]) -> bool:
    """Return True if all coordinate values are in the [0.0, 1.0] range."""
    return all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in points)


def _assign_corners(points: list[tuple[float, float]]) -> dict:
    """
    Map exactly 4 (x, y) points to named corners: tl, tr, br, bl.

    Strategy:
      - Sort all 4 by y ascending  →  top-2 and bottom-2
      - Within each pair sort by x →  left / right
      → top-left, top-right, bottom-left, bottom-right
    """
    if len(points) != 4:
        raise ValueError("Corner JSON requires exactly 4 polygon points.")
    by_y = sorted(points, key=lambda p: p[1])
    tl, tr = sorted(by_y[:2], key=lambda p: p[0])
    bl, br = sorted(by_y[2:], key=lambda p: p[0])
    return {"tl": tl, "tr": tr, "br": br, "bl": bl}


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

POLY_FILL    = (0, 229, 192, 50)
POLY_OUTLINE = (0, 229, 192, 255)
PT_FIRST     = (255, 215, 0)
PT_NORMAL    = (255, 107, 53)
PT_RADIUS    = 6
LINE_WIDTH   = 2


def _draw_polygon_overlay(img: Image.Image, points: list, closed: bool = True,
                          line_width: int = LINE_WIDTH, pt_radius: int = PT_RADIUS) -> Image.Image:
    """Draw a polygon overlay on a PIL Image.  Returns a new image."""
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

    for i, pt in enumerate(points):
        color = PT_FIRST if i == 0 else PT_NORMAL
        r = pt_radius
        draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r],
                     fill=color, outline=(255, 255, 255, 255), width=2)

    out = Image.alpha_composite(out, overlay)
    return out.convert("RGB")


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
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
    """
    Interactive canvas for drawing an ROI polygon on an image.

    - Left-click  : place a vertex
    - Right-click : remove last vertex
    - Click near first point (or press Close) : close the polygon
    """

    points_changed = pyqtSignal(list, bool)   # (points, is_closed)

    SNAP_RADIUS = 14   # px in display space

    def __init__(self):
        super().__init__()
        self.orig_image: Image.Image | None = None
        self._display_pix: QPixmap | None = None
        self._scale: float = 1.0
        self._offset_x: int = 0
        self._offset_y: int = 0

        self.points: list[tuple[int, int]] = []
        self.closed: bool = False
        self._hover: tuple[int, int] | None = None   # label-space

        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(500, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_image(self, path: str):
        self.orig_image = Image.open(path).convert("RGB")
        self.points = []
        self.closed = False
        self._hover = None
        self._render()
        self.points_changed.emit(self.points, self.closed)
        self.setStyleSheet("QLabel { background-color: #1a1a2e; border: 2px solid #2e2e50; }")

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
        out = _draw_polygon_overlay(self.orig_image, self.points, closed=self.closed,
                                    line_width=3, pt_radius=8)
        out.save(path)
        return True

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

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

        # Build display image (scaled)
        disp = self.orig_image.resize((dw, dh), Image.LANCZOS).convert("RGBA")
        overlay = Image.new("RGBA", (dw, dh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Scale points to display coords
        spts = [(int(x * scale), int(y * scale)) for x, y in self.points]

        # Filled polygon
        if len(spts) >= 3:
            draw.polygon(spts, fill=POLY_FILL)

        # Lines
        if len(spts) >= 2:
            for i in range(len(spts) - 1):
                draw.line([spts[i], spts[i + 1]], fill=POLY_OUTLINE, width=LINE_WIDTH)
            if self.closed:
                draw.line([spts[-1], spts[0]], fill=POLY_OUTLINE, width=LINE_WIDTH)

        # Hover preview line (dotted via short segments)
        if self._hover and not self.closed and spts:
            hx = self._hover[0] - self._offset_x
            hy = self._hover[1] - self._offset_y
            x0, y0 = spts[-1]
            # Draw dashed line manually
            steps = max(abs(hx - x0), abs(hy - y0))
            if steps > 0:
                for s in range(0, steps, 8):
                    t = s / steps
                    px = int(x0 + (hx - x0) * t)
                    py = int(y0 + (hy - y0) * t)
                    draw.ellipse([px - 1, py - 1, px + 1, py + 1],
                                 fill=(0, 229, 192, 140))

        # Snap indicator: highlight first point when hovering close
        snap = self._is_near_first(self._hover) if self._hover else False

        # Points
        r = PT_RADIUS
        for i, pt in enumerate(spts):
            if i == 0 and snap and not self.closed:
                color = (255, 255, 0, 255)
                cr = r + 3
            else:
                color = (PT_FIRST if i == 0 else PT_NORMAL) + (255,)
                cr = r
            draw.ellipse([pt[0] - cr, pt[1] - cr, pt[0] + cr, pt[1] + cr],
                         fill=color, outline=(255, 255, 255, 230), width=2)
            # Index label
            draw.text((pt[0] + cr + 3, pt[1] - cr), str(i + 1),
                      fill=(255, 255, 255, 220))

        # Compose
        disp = Image.alpha_composite(disp, overlay).convert("RGB")
        self.setPixmap(_pil_to_qpixmap(disp))

    # ------------------------------------------------------------------
    # Coordinate conversion helpers
    # ------------------------------------------------------------------

    def _label_to_image(self, label_pos) -> tuple[int, int] | None:
        if not self.orig_image or not self._scale:
            return None
        px = label_pos.x() - self._offset_x
        py = label_pos.y() - self._offset_y
        dw = int(self.orig_image.width * self._scale)
        dh = int(self.orig_image.height * self._scale)
        if px < 0 or py < 0 or px >= dw or py >= dh:
            return None
        iw, ih = self.orig_image.size
        return (
            max(0, min(iw - 1, int(px / self._scale))),
            max(0, min(ih - 1, int(py / self._scale))),
        )

    def _is_near_first(self, label_pos) -> bool:
        """True if label_pos is within SNAP_RADIUS of first point (display coords)."""
        if not self.points or not label_pos:
            return False
        fx = int(self.points[0][0] * self._scale) + self._offset_x
        fy = int(self.points[0][1] * self._scale) + self._offset_y
        dx = label_pos[0] - fx
        dy = label_pos[1] - fy
        return (dx * dx + dy * dy) ** 0.5 < self.SNAP_RADIUS

    # ------------------------------------------------------------------
    # Mouse / resize events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if not self.orig_image or self.closed:
            return
        if event.button() == Qt.LeftButton:
            pos = (event.pos().x(), event.pos().y())
            # Snap to close
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
    """Read-only canvas that overlays a polygon from provided coordinates."""

    def __init__(self):
        super().__init__()
        self.orig_image: Image.Image | None = None
        self._points: list[tuple[int, int]] = []

        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(500, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()

    def _show_placeholder(self):
        self.setText(
            "Load an image and paste coordinates,\n"
            "then click  Visualize ROI"
        )
        self.setStyleSheet(
            "QLabel { background-color: #1a1a2e; border: 2px dashed #2e2e50;"
            " color: #8888aa; font-size: 13px; }"
        )

    def load_image(self, path: str):
        self.orig_image = Image.open(path).convert("RGB")
        self._points = []
        self._render()
        self.setStyleSheet("QLabel { background-color: #1a1a2e; border: 2px solid #2e2e50; }")

    def set_polygon(self, points: list[tuple[int, int]]):
        self._points = points
        self._render()

    def clear_polygon(self):
        self._points = []
        self._render()

    def save_image(self, path: str) -> bool:
        if not self.orig_image:
            return False
        out = _draw_polygon_overlay(self.orig_image, self._points, closed=True,
                                    line_width=3, pt_radius=8)
        out.save(path)
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
        ("JSON Array",       "[[x, y], ...]"),
        ("Python List",      "[(x, y), ...]"),
        ("Space-separated",  "x,y x,y ..."),
        ("Flat CSV",         "x1,y1,x2,y2,..."),
        ("Corner JSON",      "{\"tl\":{x,y}, \"tr\":{x,y}, \"br\":{x,y}, \"bl\":{x,y}}"),
    ]

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._setup_shortcuts()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left: canvas area ----------------------------------------
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        llay.setSpacing(6)

        # Toolbar row
        tbar = QHBoxLayout()
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        tbar.addWidget(self.load_btn)
        tbar.addStretch()
        hint = QLabel(
            "Left-click: add point  ·  Right-click / Ctrl+Z: undo  ·  "
            "Click near ① or press 'Close Polygon': close shape"
        )
        hint.setStyleSheet("color: #8888aa; font-size: 11px;")
        tbar.addWidget(hint)
        llay.addLayout(tbar)

        self.canvas = DrawingCanvas()
        self.canvas.points_changed.connect(self._on_points_changed)
        llay.addWidget(self.canvas)

        splitter.addWidget(left)

        # ---- Right: controls ------------------------------------------
        right = QWidget()
        right.setMinimumWidth(270)
        right.setMaximumWidth(310)
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(8)

        # Info
        info_box = QGroupBox("Image Info")
        info_lay = QVBoxLayout(info_box)
        self.lbl_size   = QLabel("Size: —")
        self.lbl_pts    = QLabel("Points: 0")
        self.lbl_status = QLabel("Load an image to begin")
        for lbl in (self.lbl_size, self.lbl_pts, self.lbl_status):
            lbl.setStyleSheet("color: #8888aa; font-size: 12px;")
        info_lay.addWidget(self.lbl_size)
        info_lay.addWidget(self.lbl_pts)
        info_lay.addWidget(self.lbl_status)
        rlay.addWidget(info_box)

        # Drawing controls
        ctrl_box = QGroupBox("Controls")
        ctrl_lay = QVBoxLayout(ctrl_box)

        self.btn_close = QPushButton("Close Polygon")
        self.btn_close.setObjectName("success")
        self.btn_close.clicked.connect(self.canvas.close_polygon)
        self.btn_close.setEnabled(False)
        ctrl_lay.addWidget(self.btn_close)

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
        ctrl_lay.addLayout(row)
        rlay.addWidget(ctrl_box)

        # Format selector
        fmt_box = QGroupBox("Output Format")
        fmt_lay = QVBoxLayout(fmt_box)
        self.fmt_combo = QComboBox()
        for label, example in self.FORMATS:
            self.fmt_combo.addItem(f"{label}  —  {example}")
        self.fmt_combo.currentIndexChanged.connect(self._update_output)
        fmt_lay.addWidget(self.fmt_combo)

        self.chk_normalize = QCheckBox("Normalize coordinates  (x / width, y / height  →  0.0–1.0)")
        self.chk_normalize.setToolTip(
            "Divide each x by image width and each y by image height.\n"
            "Output values will be in the range [0.0, 1.0]."
        )
        self.chk_normalize.stateChanged.connect(self._update_output)
        fmt_lay.addWidget(self.chk_normalize)
        rlay.addWidget(fmt_box)

        # Coordinates output
        out_box = QGroupBox("Coordinates")
        out_lay = QVBoxLayout(out_box)
        self.coord_out = QTextEdit()
        self.coord_out.setReadOnly(True)
        self.coord_out.setMinimumHeight(130)
        self.coord_out.setMaximumHeight(200)
        self.coord_out.setPlaceholderText("Coordinates appear here once you place points…")
        out_lay.addWidget(self.coord_out)

        self.btn_copy = QPushButton("Copy to Clipboard")
        self.btn_copy.setObjectName("blue")
        self.btn_copy.clicked.connect(self._copy_coords)
        out_lay.addWidget(self.btn_copy)
        rlay.addWidget(out_box)

        # Export
        exp_box = QGroupBox("Export")
        exp_lay = QVBoxLayout(exp_box)
        btn_save = QPushButton("Save Image with ROI overlay")
        btn_save.setObjectName("secondary")
        btn_save.clicked.connect(self._save_image)
        exp_lay.addWidget(btn_save)
        rlay.addWidget(exp_box)

        rlay.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([750, 290])
        root.addWidget(splitter)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo_last)
        QShortcut(QKeySequence("Escape"), self, self.canvas.clear_all)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*)"
        )
        if not path:
            return
        self.canvas.load_image(path)
        w, h = self.canvas.orig_image.size
        self.lbl_size.setText(f"Size: {w} × {h} px")
        self.lbl_status.setText("Click on the image to place polygon vertices")

    def _on_points_changed(self, points: list, closed: bool):
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
            self.lbl_status.setText(f"Need {3 - n} more point(s) to close polygon")
        else:
            self.lbl_status.setText("Click near ① or press 'Close Polygon'")

        self._update_output()

    def _update_output(self):
        raw_points = self.canvas.points
        if not raw_points:
            self.coord_out.setPlainText("")
            return

        # Apply normalization if requested
        normalize = self.chk_normalize.isChecked()
        if normalize and self.canvas.orig_image:
            iw, ih = self.canvas.orig_image.size
            points = [(x / iw, y / ih) for x, y in raw_points]
            fmt_val = lambda v: f"{v:.6f}"
            # For JSON-native numbers: round to 6 decimal places
            num_val = lambda v: round(v, 6)
        else:
            points = raw_points
            fmt_val = lambda v: str(v)
            num_val = lambda v: v

        idx = self.fmt_combo.currentIndex()
        if idx == 0:   # JSON Array
            lines = [f"  [{fmt_val(x)}, {fmt_val(y)}]" for x, y in points]
            text = "[\n" + ",\n".join(lines) + "\n]"
        elif idx == 1:  # Python List
            lines = [f"  ({fmt_val(x)}, {fmt_val(y)})" for x, y in points]
            text = "[\n" + ",\n".join(lines) + "\n]"
        elif idx == 2:  # Space-separated pairs
            text = "  ".join(f"{fmt_val(x)},{fmt_val(y)}" for x, y in points)
        elif idx == 3:  # Flat CSV
            flat = [fmt_val(v) for x, y in points for v in (x, y)]
            text = ", ".join(flat)
        else:           # Corner JSON  (idx == 4)
            if len(points) != 4:
                text = (
                    f"# Corner JSON requires exactly 4 points.\n"
                    f"# Currently {len(points)} point(s) placed.\n"
                    f"# Place 4 vertices and this format will update automatically."
                )
            else:
                corners = _assign_corners(points)
                roi_dict = {
                    "roi": {
                        k: {"x": num_val(corners[k][0]), "y": num_val(corners[k][1])}
                        for k in ("tl", "tr", "br", "bl")
                    }
                }
                text = json.dumps(roi_dict, indent=4)

        self.coord_out.setPlainText(text)

    def _copy_coords(self):
        text = self.coord_out.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_image(self):
        if not self.canvas.orig_image:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
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

        # ---- Left: canvas area ----------------------------------------
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        llay.setSpacing(6)

        tbar = QHBoxLayout()
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        tbar.addWidget(self.load_btn)
        tbar.addStretch()
        self.lbl_img = QLabel("No image loaded")
        self.lbl_img.setStyleSheet("color: #8888aa; font-size: 11px;")
        tbar.addWidget(self.lbl_img)
        llay.addLayout(tbar)

        self.canvas = VisCanvas()
        llay.addWidget(self.canvas)

        splitter.addWidget(left)

        # ---- Right: controls ------------------------------------------
        right = QWidget()
        right.setMinimumWidth(270)
        right.setMaximumWidth(310)
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        rlay.setSpacing(8)

        # Coordinate input
        cin_box = QGroupBox("Paste Coordinates")
        cin_lay = QVBoxLayout(cin_box)
        fmt_hint = QLabel(
            "Accepted formats:\n"
            "  [[x,y], [x,y], …]   (JSON)\n"
            "  [(x,y), (x,y), …]   (Python)\n"
            "  x,y x,y …           (space-sep)\n"
            "  x1,y1,x2,y2,…       (flat CSV)"
        )
        fmt_hint.setStyleSheet("color: #8888aa; font-size: 11px; line-height: 1.5;")
        cin_lay.addWidget(fmt_hint)

        self.coord_in = QTextEdit()
        self.coord_in.setMinimumHeight(130)
        self.coord_in.setMaximumHeight(200)
        self.coord_in.setPlaceholderText("Paste your coordinates here…")
        cin_lay.addWidget(self.coord_in)

        self.chk_normalized = QCheckBox("Coordinates are normalized  (0.0–1.0  →  scale to image size)")
        self.chk_normalized.setToolTip(
            "When checked, each x is multiplied by image width\n"
            "and each y is multiplied by image height.\n\n"
            "Leave unchecked for regular pixel coordinates."
        )
        cin_lay.addWidget(self.chk_normalized)
        rlay.addWidget(cin_box)

        # Buttons
        self.btn_vis = QPushButton("Visualize ROI")
        self.btn_vis.setObjectName("teal")
        self.btn_vis.setStyleSheet(
            "QPushButton { background-color: #0d9488; color: #f0fdfa;"
            " font-size: 14px; padding: 10px; }"
            "QPushButton:hover { background-color: #0f766e; }"
        )
        self.btn_vis.clicked.connect(self._visualize)
        rlay.addWidget(self.btn_vis)

        btn_clear = QPushButton("Clear ROI")
        btn_clear.setObjectName("secondary")
        btn_clear.clicked.connect(self._clear_roi)
        rlay.addWidget(btn_clear)

        QShortcut(QKeySequence("Return"), self, self._visualize)

        # Info
        info_box = QGroupBox("ROI Info")
        info_lay = QVBoxLayout(info_box)
        self.lbl_roi_status = QLabel("No ROI loaded")
        self.lbl_roi_status.setStyleSheet("color: #8888aa; font-size: 12px;")
        self.lbl_roi_pts = QLabel("")
        self.lbl_roi_pts.setStyleSheet("color: #8888aa; font-size: 11px;")
        self.lbl_roi_pts.setWordWrap(True)
        info_lay.addWidget(self.lbl_roi_status)
        info_lay.addWidget(self.lbl_roi_pts)
        rlay.addWidget(info_box)

        # Export
        exp_box = QGroupBox("Export")
        exp_lay = QVBoxLayout(exp_box)
        btn_save = QPushButton("Save Image with ROI overlay")
        btn_save.setObjectName("secondary")
        btn_save.clicked.connect(self._save_image)
        exp_lay.addWidget(btn_save)
        rlay.addWidget(exp_box)

        rlay.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([750, 290])
        root.addWidget(splitter)

    # ------------------------------------------------------------------

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*)"
        )
        if not path:
            return
        self.canvas.load_image(path)
        w, h = self.canvas.orig_image.size
        self.lbl_img.setText(f"{w} × {h} px")

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
                raise ValueError("At least 2 points are required to draw a polygon.")

            # Scale normalized coords → pixel coords
            if self.chk_normalized.isChecked():
                iw, ih = self.canvas.orig_image.size
                # Validate range
                if not _is_normalized(parsed):
                    raise ValueError(
                        "Some coordinate values are outside [0.0, 1.0].\n"
                        "Uncheck 'Coordinates are normalized' if you are "
                        "using pixel coordinates."
                    )
                points = [(int(round(x * iw)), int(round(y * ih))) for x, y in parsed]
            else:
                points = [(int(round(x)), int(round(y))) for x, y in parsed]

            self.canvas.set_polygon(points)
            norm_tag = "  (normalized → pixel)" if self.chk_normalized.isChecked() else ""
            self.lbl_roi_status.setText(f"ROI visualized  ({len(points)} vertices){norm_tag}")
            preview = "  ".join(f"({x},{y})" for x, y in points[:6])
            if len(points) > 6:
                preview += f"  … +{len(points) - 6} more"
            self.lbl_roi_pts.setText(preview)
        except ValueError as exc:
            QMessageBox.critical(self, "Parse Error", str(exc))

    def _clear_roi(self):
        self.canvas.clear_polygon()
        self.lbl_roi_status.setText("No ROI loaded")
        self.lbl_roi_pts.setText("")

    def _save_image(self):
        if not self.canvas.orig_image:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if path and self.canvas.save_image(path):
            QMessageBox.information(self, "Saved", f"Image saved:\n{path}")


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROI Polygon Drawer & Visualizer")
        self.setMinimumSize(900, 640)
        self.resize(1200, 760)

        tabs = QTabWidget()
        tabs.addTab(DrawROITab(),       "  ✏  Draw ROI  ")
        tabs.addTab(VisualizeROITab(),  "  👁  Visualize ROI  ")
        self.setCentralWidget(tabs)

        sb = QStatusBar()
        sb.showMessage(
            "Draw ROI: click to place vertices, right-click to undo, "
            "close the polygon to export coordinates  |  "
            "Visualize ROI: load image, paste coordinates, click Visualize"
        )
        self.setStatusBar(sb)


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
