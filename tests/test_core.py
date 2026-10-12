"""Tests for the box logic (no window needed)."""

import pytest

from yolo_core import (Annotator, View, box_problems, check_dataset, from_yolo,
                       read_labels, to_yolo, write_labels)


def test_yolo_round_trip():
    box = (2, 100, 50, 300, 250)
    row = to_yolo(box, 1000, 500)
    assert row == pytest.approx((2, 0.2, 0.3, 0.2, 0.4))
    assert from_yolo(row, 1000, 500) == pytest.approx(box)


def test_box_drawn_right_to_left_is_still_valid():
    # dragging up-left used to give a negative width
    row = to_yolo((0, 300, 250, 100, 50), 1000, 500)
    assert row[3] > 0 and row[4] > 0
    assert box_problems(row) == []


def test_box_is_clipped_to_image():
    row = to_yolo((0, -40, -40, 120, 60), 200, 100)
    assert box_problems(row) == []
    assert row == pytest.approx((0, 0.3, 0.3, 0.6, 0.6))


def test_box_drawn_while_zoomed_lands_in_the_right_place():
    ann = Annotator(800, 600)
    ann.view.zoom_at(400, 300, 2.0)          # zoom 2x on the centre -> view shows x 200..600, y 150..450
    ann.press(0, 0)
    ann.release(400, 300)                    # half of the screen = a quarter of the image
    assert ann.boxes[0][1:] == pytest.approx((200, 150, 400, 300))


def test_zoom_keeps_point_under_cursor():
    view = View(800, 600)
    before = view.to_image(100, 100)
    view.zoom_at(100, 100, 3.0)
    assert view.to_image(100, 100) == pytest.approx(before)


def test_pan_stays_inside_image():
    view = View(800, 600)
    view.zoom_at(400, 300, 2.0)
    view.pan(-10_000, -10_000)
    assert view.crop[:2] == (0, 0)


def test_click_without_drag_creates_no_box():
    ann = Annotator(800, 600)
    ann.press(50, 50)
    assert ann.release(51, 50) is False
    assert ann.boxes == []


def test_undo_redo_one_step_at_a_time():
    ann = Annotator(800, 600)
    for x in (10, 100, 200):
        ann.press(x, 10)
        ann.release(x + 50, 60)
    ann.undo()
    assert len(ann.boxes) == 2               # the old version removed two boxes per undo
    ann.undo()
    assert len(ann.boxes) == 1
    ann.redo()
    assert len(ann.boxes) == 2


def test_change_class_of_selected_box():
    ann = Annotator(800, 600, [(0, 10, 10, 100, 100)])
    ann.select_at(50, 50)
    ann.set_class(3)
    assert ann.boxes[0][0] == 3
    ann.undo()
    assert ann.boxes[0][0] == 0


def test_select_prefers_inner_box():
    ann = Annotator(800, 600, [(0, 0, 0, 500, 500), (1, 100, 100, 150, 150)])
    ann.select_at(120, 120)
    assert ann.selected == 1


def test_problems_detected():
    assert "zero-size box" in box_problems((5, 0.22, 0.56, 0.0, 0.0))
    assert "outside image" in box_problems((0, 0.95, 0.5, 0.2, 0.2))
    assert "unknown class" in box_problems((7, 0.5, 0.5, 0.2, 0.2), n_classes=6)


def test_check_dataset(tmp_path):
    imgs, lbls = tmp_path / "images", tmp_path / "labels"
    imgs.mkdir(); lbls.mkdir()
    for name in ("a.jpg", "b.jpg", "c.png"):
        (imgs / name).write_bytes(b"")
    write_labels(str(lbls / "a.txt"), [(0, 0.5, 0.5, 0.2, 0.2), (1, 0.3, 0.3, 0.0, 0.0)])
    (lbls / "b.txt").write_text("0 0.5 0.5\n")                   # malformed line
    write_labels(str(lbls / "old.txt"), [(0, 0.5, 0.5, 0.1, 0.1)])  # no image

    report = check_dataset(str(imgs), str(lbls))
    assert (report.images, report.labelled, report.boxes) == (3, 2, 2)
    assert report.missing_labels == ["c.png"]
    assert report.orphan_labels == ["old.txt"]
    assert {i[2] for i in report.issues} == {"zero-size box", "unreadable line"}
    assert not report.ok


def test_empty_label_file_round_trip(tmp_path):
    path = str(tmp_path / "x.txt")
    write_labels(path, [])
    assert read_labels(path) == ([], [])
