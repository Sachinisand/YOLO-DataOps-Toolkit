"""
YOLO annotation toolkit: draw, review, visualise and check YOLO bounding-box labels.

    python src/yolo_manager.py annotate  --img_dir data/images --lbl_dir data/annotated_labels
    python src/yolo_manager.py visualize --img_dir data/images --lbl_dir data/annotated_labels --save_dir data/visualizations
    python src/yolo_manager.py check     --img_dir data/images --lbl_dir data/annotated_labels

The box logic lives in yolo_core.py (tested); this file is the OpenCV window and the CLI.
"""

import argparse
import os
import sys

import cv2

from yolo_core import (Annotator, check_dataset, from_yolo, label_path, list_images,
                       read_labels, save_issues_csv, write_labels)

WINDOW = "YOLO annotation"
MAX_W, MAX_H = 1600, 950
GREEN, RED, YELLOW, BLUE = (0, 200, 0), (0, 0, 255), (0, 255, 255), (255, 0, 0)

# Arrow-key codes differ between OpenCV builds (Linux / Windows / macOS)
ARROWS = {"left": {81, 65361, 2424832, 63234}, "up": {82, 65362, 2490368, 63232},
          "right": {83, 65363, 2555904, 63235}, "down": {84, 65364, 2621440, 63233}}
HELP = ("drag: draw   right-click: select   0-9: class",
        "x: delete   c: clear   u / y: undo / redo",
        "+ / -: zoom at cursor   arrows: pan   r: reset",
        "q: save + next   s: skip   esc: save + stop   h: hide help")


def fit_to_screen(img):
    """Shrink large images so they fit the window. Labels are relative, so this does not change them."""
    scale = min(MAX_W / img.shape[1], MAX_H / img.shape[0], 1.0)
    return cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img


def render(img, ann: Annotator, mouse, drawing_box, brightness, contrast, show_help=True):
    view = ann.view
    x0, y0, w, h = view.crop
    crop = img[int(y0):int(y0 + h), int(x0):int(x0 + w)]
    canvas = cv2.resize(crop, (view.img_w, view.img_h), interpolation=cv2.INTER_LINEAR)
    canvas = cv2.convertScaleAbs(canvas, alpha=contrast, beta=brightness)

    boxes = [(i, b) for i, b in enumerate(ann.boxes)] + ([(-1, drawing_box)] if drawing_box else [])
    for i, (cls, x1, y1, x2, y2) in boxes:
        p1 = tuple(int(v) for v in view.to_display(x1, y1))
        p2 = tuple(int(v) for v in view.to_display(x2, y2))
        colour = RED if i == ann.selected else YELLOW if i == -1 else GREEN
        cv2.rectangle(canvas, p1, p2, colour, 3 if i == ann.selected else 2)
        cv2.putText(canvas, str(cls), (min(p1[0], p2[0]), min(p1[1], p2[1]) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)

    mx, my = mouse
    cv2.line(canvas, (mx - 12, my), (mx + 12, my), BLUE, 1)
    cv2.line(canvas, (mx, my - 12), (mx, my + 12), BLUE, 1)
    status = f"boxes: {len(ann.boxes)}   class: {ann.current_class}   zoom: {view.zoom:.1f}x"
    lines = (status, *HELP) if show_help else (status,)
    band = canvas[:12 + 22 * len(lines)].copy()
    cv2.rectangle(band, (0, 0), (band.shape[1], band.shape[0]), (0, 0, 0), -1)
    canvas[:band.shape[0]] = cv2.addWeighted(band, 0.6, canvas[:band.shape[0]], 0.4, 0)
    for n, line in enumerate(lines):
        cv2.putText(canvas, line, (10, 24 + 22 * n), cv2.FONT_HERSHEY_SIMPLEX, 0.5, YELLOW if n == 0 else (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def annotate_image(img_path, rows):
    """Open one image with its existing boxes. Returns (yolo_rows or None if skipped, stop_session)."""
    img = fit_to_screen(cv2.imread(img_path))
    h, w = img.shape[:2]
    ann = Annotator(w, h, [from_yolo(r, w, h) for r in rows])
    ui = {"mouse": (0, 0), "drawing": None, "help": True}

    def on_mouse(event, x, y, flags, _):
        ui["mouse"] = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            ann.press(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            ui["drawing"] = ann.drag(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            ann.release(x, y)
            ui["drawing"] = None
        elif event == cv2.EVENT_RBUTTONDOWN:
            ann.select_at(x, y)

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW, on_mouse)
    cv2.createTrackbar("brightness", WINDOW, 50, 100, lambda v: None)
    cv2.createTrackbar("contrast x10", WINDOW, 10, 30, lambda v: None)
    cv2.setWindowTitle(WINDOW, f"{WINDOW} - {os.path.basename(img_path)}")

    while True:
        brightness = cv2.getTrackbarPos("brightness", WINDOW) - 50
        contrast = max(cv2.getTrackbarPos("contrast x10", WINDOW), 1) / 10
        cv2.imshow(WINDOW, render(img, ann, ui["mouse"], ui["drawing"], brightness, contrast, ui["help"]))
        key = cv2.waitKeyEx(15)
        if key == -1:
            continue
        char = chr(key & 0xFF) if key & 0xFF < 128 else ""
        if char == "q":
            return ann.yolo_rows(), False
        if key == 27:                        # Esc
            return ann.yolo_rows(), True
        if char == "s":
            return None, False
        if char.isdigit():
            ann.set_class(int(char))
        elif char == "h":
            ui["help"] = not ui["help"]
        elif char == "x":
            ann.delete_selected()
        elif char == "c":
            ann.clear()
        elif char == "u":
            ann.undo()
        elif char == "y":
            ann.redo()
        elif char and char in "+=":
            ann.view.zoom_at(*ui["mouse"], 1.25)
        elif char == "-":
            ann.view.zoom_at(*ui["mouse"], 1 / 1.25)
        elif char == "r":
            ann.view.reset()
            cv2.setTrackbarPos("brightness", WINDOW, 50)
            cv2.setTrackbarPos("contrast x10", WINDOW, 10)
        else:
            for direction, (dx, dy) in {"left": (-60, 0), "right": (60, 0), "up": (0, -60), "down": (0, 60)}.items():
                if key in ARROWS[direction]:
                    ann.view.pan(dx, dy)


def cmd_annotate(args):
    """Annotate images; existing labels are loaded, so this is also the review mode."""
    out_dir = args.save_dir or args.lbl_dir
    images = list_images(args.img_dir)
    print(f"{len(images)} images in {args.img_dir}; labels read from {args.lbl_dir}, saved to {out_dir}")
    for n, path in enumerate(images, 1):
        rows, problems = read_labels(label_path(path, args.lbl_dir))
        for p in problems:
            print(f"  warning {os.path.basename(path)}: {p}")
        print(f"[{n}/{len(images)}] {os.path.basename(path)} ({len(rows)} existing boxes)")
        new_rows, stop = annotate_image(path, rows)
        if new_rows is not None:
            write_labels(label_path(path, out_dir), new_rows)
            print(f"  saved {len(new_rows)} boxes")
        if stop:
            break
    cv2.destroyAllWindows()


def cmd_visualize(args):
    os.makedirs(args.save_dir, exist_ok=True)
    written = 0
    for path in list_images(args.img_dir):
        rows, _ = read_labels(label_path(path, args.lbl_dir))
        if not rows:
            continue
        img = cv2.imread(path)
        h, w = img.shape[:2]
        thickness = max(2, round(max(h, w) / 400))
        for row in rows:
            cls, x1, y1, x2, y2 = from_yolo(row, w, h)
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), GREEN, thickness)
            cv2.putText(img, str(cls), (int(x1), max(int(y1) - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, thickness / 2.5, GREEN, thickness)
        cv2.imwrite(os.path.join(args.save_dir, "vis_" + os.path.basename(path)), img)
        written += 1
    print(f"wrote {written} images to {args.save_dir}")


def cmd_check(args):
    report = check_dataset(args.img_dir, args.lbl_dir, args.classes)
    print(f"images: {report.images} | with labels: {report.labelled} | boxes: {report.boxes}")
    print("boxes per class: " + ", ".join(f"{c}: {n}" for c, n in sorted(report.class_counts.items())))
    for f in report.missing_labels:
        print(f"  missing label   {f}")
    for f in report.orphan_labels:
        print(f"  label w/o image {f}")
    for f, where, issue in report.issues:
        print(f"  {issue:<15} {f} {where}")
    if args.report:
        save_issues_csv(report, args.report)
        print(f"issue list saved to {args.report}")
    print("OK" if report.ok else f"{len(report.issues) + len(report.missing_labels) + len(report.orphan_labels)} problem(s) found")
    return 0 if report.ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw, review, visualise and check YOLO labels.")
    parser.add_argument("mode", choices=["annotate", "review", "visualize", "check"])
    parser.add_argument("--img_dir", required=True)
    parser.add_argument("--lbl_dir", required=True, help="folder with YOLO .txt labels (read)")
    parser.add_argument("--save_dir", help="annotate/review: where to write labels (default: lbl_dir); visualize: output folder")
    parser.add_argument("--classes", type=int, help="check: number of classes, to flag unknown class ids")
    parser.add_argument("--report", help="check: write the issue list to this CSV")
    args = parser.parse_args(argv)

    if args.mode in ("annotate", "review"):
        cmd_annotate(args)
    elif args.mode == "visualize":
        if not args.save_dir:
            parser.error("visualize needs --save_dir")
        cmd_visualize(args)
    else:
        return cmd_check(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
