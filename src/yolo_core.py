"""
Pure logic for the YOLO annotation toolkit (no windows, so it can be tested).

Coordinates
-----------
- Boxes are kept in *image pixels* as (class_id, x1, y1, x2, y2).
- The screen shows a *view*: a crop of the image (when zoomed) scaled to the window.
  View.to_image() / View.to_display() convert between the two, so a box drawn while
  zoomed in lands in the right place in the saved label.
- YOLO label files store: class x_center y_center width height, all relative (0-1).
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from dataclasses import dataclass, field
from glob import glob

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")
MIN_BOX_PX = 3          # boxes smaller than this (a click without a drag) are ignored


# ---------------------------------------------------------------- boxes and labels

def to_yolo(box, img_w: int, img_h: int):
    """Pixel box -> YOLO row. Corners are sorted (drawing right-to-left is fine)
    and clipped to the image."""
    cls, x1, y1, x2, y2 = box
    x1, x2 = sorted((min(max(x1, 0), img_w), min(max(x2, 0), img_w)))
    y1, y2 = sorted((min(max(y1, 0), img_h), min(max(y2, 0), img_h)))
    w, h = x2 - x1, y2 - y1
    return (int(cls), (x1 + w / 2) / img_w, (y1 + h / 2) / img_h, w / img_w, h / img_h)


def from_yolo(row, img_w: int, img_h: int):
    """YOLO row -> pixel box."""
    cls, xc, yc, w, h = row
    return (int(cls), (xc - w / 2) * img_w, (yc - h / 2) * img_h,
            (xc + w / 2) * img_w, (yc + h / 2) * img_h)


def read_labels(path: str):
    """Read a YOLO label file. Returns (rows, problems) — malformed lines are reported, not crashed on."""
    rows, problems = [], []
    if not os.path.exists(path):
        return rows, problems
    with open(path) as fh:
        for n, line in enumerate(fh, 1):
            parts = line.split()
            if not parts:
                continue
            try:
                if len(parts) != 5:
                    raise ValueError
                cls = float(parts[0])
                if cls != int(cls):
                    raise ValueError
                rows.append((int(cls), *map(float, parts[1:])))
            except ValueError:
                problems.append(f"line {n}: cannot parse '{line.strip()}'")
    return rows, problems


def write_labels(path: str, rows) -> None:
    """Write YOLO rows. An empty list writes an empty file (= image with no objects)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        for cls, xc, yc, w, h in rows:
            fh.write(f"{int(cls)} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")


def box_problems(row, n_classes: int | None = None, min_size: float = 0.002):
    """Return the reasons a YOLO row is invalid (empty list = valid)."""
    cls, xc, yc, w, h = row
    reasons = []
    if cls < 0 or (n_classes is not None and cls >= n_classes):
        reasons.append("unknown class")
    if w <= min_size or h <= min_size:
        reasons.append("zero-size box")
    if not (0 <= xc - w / 2 + 1e-6 and xc + w / 2 - 1e-6 <= 1 and 0 <= yc - h / 2 + 1e-6 and yc + h / 2 - 1e-6 <= 1):
        reasons.append("outside image")
    return reasons


# ---------------------------------------------------------------- dataset check

def list_images(img_dir: str):
    return sorted(p for p in glob(os.path.join(img_dir, "*")) if p.lower().endswith(IMAGE_EXTENSIONS))


def label_path(img_path: str, lbl_dir: str) -> str:
    return os.path.join(lbl_dir, os.path.splitext(os.path.basename(img_path))[0] + ".txt")


@dataclass
class CheckReport:
    images: int = 0
    labelled: int = 0
    boxes: int = 0
    class_counts: Counter = field(default_factory=Counter)
    missing_labels: list = field(default_factory=list)
    orphan_labels: list = field(default_factory=list)
    issues: list = field(default_factory=list)      # (file, line/box, reason)

    @property
    def ok(self) -> bool:
        return not (self.missing_labels or self.orphan_labels or self.issues)


def check_dataset(img_dir: str, lbl_dir: str, n_classes: int | None = None) -> CheckReport:
    """Quality report for an image folder and its YOLO labels."""
    report = CheckReport()
    images = list_images(img_dir)
    report.images = len(images)
    stems = {os.path.splitext(os.path.basename(p))[0] for p in images}

    for img in images:
        path = label_path(img, lbl_dir)
        name = os.path.basename(path)
        if not os.path.exists(path):
            report.missing_labels.append(os.path.basename(img))
            continue
        report.labelled += 1
        rows, problems = read_labels(path)
        report.issues += [(name, p.split(":")[0], "unreadable line") for p in problems]
        for i, row in enumerate(rows, 1):
            report.boxes += 1
            report.class_counts[row[0]] += 1
            for reason in box_problems(row, n_classes):
                report.issues.append((name, f"box {i}", reason))

    if os.path.isdir(lbl_dir):
        report.orphan_labels = sorted(f for f in os.listdir(lbl_dir)
                                      if f.endswith(".txt") and os.path.splitext(f)[0] not in stems)
    return report


def save_issues_csv(report: CheckReport, path: str) -> None:
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["file", "where", "issue"])
        writer.writerows(report.issues)
        writer.writerows((f, "", "no label file") for f in report.missing_labels)
        writer.writerows((f, "", "label without image") for f in report.orphan_labels)


# ---------------------------------------------------------------- view (zoom and pan)

@dataclass
class View:
    """Which part of the image is on screen. zoom=1 shows the whole image."""
    img_w: int
    img_h: int
    zoom: float = 1.0
    cx: float = None    # centre of the view in image pixels
    cy: float = None
    max_zoom: float = 8.0

    def __post_init__(self):
        self.reset()

    def reset(self):
        self.zoom, self.cx, self.cy = 1.0, self.img_w / 2, self.img_h / 2

    @property
    def crop(self):
        """(x0, y0, w, h) of the visible part, kept inside the image."""
        w, h = self.img_w / self.zoom, self.img_h / self.zoom
        x0 = min(max(self.cx - w / 2, 0), self.img_w - w)
        y0 = min(max(self.cy - h / 2, 0), self.img_h - h)
        return x0, y0, w, h

    def to_image(self, dx, dy):
        x0, y0, w, h = self.crop
        return x0 + dx * w / self.img_w, y0 + dy * h / self.img_h

    def to_display(self, ix, iy):
        x0, y0, w, h = self.crop
        return (ix - x0) * self.img_w / w, (iy - y0) * self.img_h / h

    def zoom_at(self, dx, dy, factor):
        """Zoom so the point under the cursor stays under the cursor."""
        ix, iy = self.to_image(dx, dy)
        self.zoom = min(max(self.zoom * factor, 1.0), self.max_zoom)
        _, _, w, h = self.crop
        self.cx = ix - (dx / self.img_w - 0.5) * w
        self.cy = iy - (dy / self.img_h - 0.5) * h
        x0, y0, w, h = self.crop               # store the clamped centre
        self.cx, self.cy = x0 + w / 2, y0 + h / 2

    def pan(self, dx_screen, dy_screen):
        _, _, w, h = self.crop
        self.cx += dx_screen * w / self.img_w
        self.cy += dy_screen * h / self.img_h
        x0, y0, w, h = self.crop
        self.cx, self.cy = x0 + w / 2, y0 + h / 2


# ---------------------------------------------------------------- annotation state

class Annotator:
    """Boxes, selection and undo/redo for one image. Mouse positions are given in
    display coordinates and converted with the View, so zoom never shifts a box."""

    def __init__(self, img_w: int, img_h: int, boxes=None):
        self.view = View(img_w, img_h)
        self.boxes = list(boxes or [])
        self.current_class = 0
        self.selected = None
        self._start = None
        self._undo, self._redo = [], []

    # history: snapshot BEFORE every change; undo restores the latest snapshot
    def _snapshot(self):
        self._undo.append(list(self.boxes))
        self._redo.clear()

    def undo(self):
        if self._undo:
            self._redo.append(list(self.boxes))
            self.boxes = self._undo.pop()
            self.selected = None

    def redo(self):
        if self._redo:
            self._undo.append(list(self.boxes))
            self.boxes = self._redo.pop()
            self.selected = None

    # mouse
    def press(self, dx, dy):
        self._start = self.view.to_image(dx, dy)

    def drag(self, dx, dy):
        """Box being drawn (for display), or None."""
        if self._start is None:
            return None
        x, y = self.view.to_image(dx, dy)
        return (self.current_class, *self._start, x, y)

    def release(self, dx, dy):
        box = self.drag(dx, dy)
        self._start = None
        if box is None:
            return False
        _, x1, y1, x2, y2 = box
        if abs(x2 - x1) < MIN_BOX_PX or abs(y2 - y1) < MIN_BOX_PX:
            return False                       # a click, not a box
        self._snapshot()
        self.boxes.append((self.current_class, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        self.selected = len(self.boxes) - 1
        return True

    def select_at(self, dx, dy):
        x, y = self.view.to_image(dx, dy)
        hits = [i for i, (_, x1, y1, x2, y2) in enumerate(self.boxes) if x1 <= x <= x2 and y1 <= y <= y2]
        # smallest box wins, so a box inside another box can still be selected
        self.selected = min(hits, key=lambda i: (self.boxes[i][3] - self.boxes[i][1]) * (self.boxes[i][4] - self.boxes[i][2])) if hits else None

    # keyboard actions
    def set_class(self, cls: int):
        """Set the class for new boxes, and for the selected box if there is one."""
        self.current_class = cls
        if self.selected is not None and self.boxes[self.selected][0] != cls:
            self._snapshot()
            self.boxes[self.selected] = (cls, *self.boxes[self.selected][1:])

    def delete_selected(self):
        if self.selected is not None:
            self._snapshot()
            self.boxes.pop(self.selected)
            self.selected = None

    def clear(self):
        if self.boxes:
            self._snapshot()
            self.boxes.clear()
            self.selected = None

    def yolo_rows(self):
        return [to_yolo(b, self.view.img_w, self.view.img_h) for b in self.boxes]
