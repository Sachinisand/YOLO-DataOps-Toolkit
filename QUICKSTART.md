# YOLO DataOps Toolkit - Quick Start Guide

## Installation & Setup

1. **Clone/Download the repository**
```bash
cd D:\github\YOLO-DataOps-Toolkit
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Quick Start Workflow

### Step 1: Prepare Your Images
Place your images in: `data/images/`

Supported formats: PNG, JPG, BMP, etc.

### Step 2: Annotate Images
```bash
python src/yolo_manager.py annotate --img_dir data/images --save_dir data/annotated_labels
```

**Controls:**
- Click & drag to draw boxes
- 0-9 to set class ID
- X to delete selected box
- +/- to zoom
- Arrow keys to pan
- R to reset view
- U/Y for undo/redo
- Q to save and next image

### Step 3: Review Annotations (Optional)
```bash
python src/yolo_manager.py review --img_dir data/images --lbl_dir data/annotated_labels --save_dir data/updated_labels
```

### Step 4: Visualize Results
```bash
python src/yolo_manager.py visualize --img_dir data/images --lbl_dir data/annotated_labels --save_dir data/visualizations
```

Check `data/visualizations/` for annotated images with boxes drawn.

## Example Workflow

```bash
# 1. Place your images in data/images/

# 2. Start annotation
python src/yolo_manager.py annotate --img_dir data/images --save_dir data/annotated_labels

# 3. View results
python src/yolo_manager.py visualize --img_dir data/images --lbl_dir data/annotated_labels --save_dir data/visualizations

# 4. Edit if needed
python src/yolo_manager.py review --img_dir data/images --lbl_dir data/annotated_labels --save_dir data/updated_labels

# 5. Final visualization
python src/yolo_manager.py visualize --img_dir data/images --lbl_dir data/updated_labels --save_dir data/visualizations
```

## Output

Labels are saved as `.txt` files in YOLO format:
```
<class_id> <x_center> <y_center> <width> <height>
```

All coordinates are normalized (0-1 range).

## Professional Features

✅ **Undo/Redo History** - Never lose work
✅ **Cursor-based Zoom** - Zoom exactly where you point
✅ **Image Enhancement** - Brightness & contrast adjustment
✅ **Batch Processing** - Annotate multiple images
✅ **Visual Verification** - Automatic visualization generation
✅ **Professional UI** - Complete keyboard shortcut support

## Tips

1. Use `+` key to zoom in for small defects/objects
2. Use `-` key to zoom out for overview
3. Right-click boxes to select them
4. Use `X` key to delete selected boxes
5. Use visualization mode to verify quality
6. Use review mode to make corrections

## Troubleshooting

**Issue**: Image not found
- Solution: Make sure images are in `data/images/` folder

**Issue**: Can't delete box
- Solution: First select the box with right-click, then press X

**Issue**: Annotation is in wrong place after zoom
- Solution: This is normal - coordinates are stored in original image space and displayed correctly

**Issue**: Labels not saving
- Solution: Check that `save_dir` exists and you have write permissions

## Support

For detailed documentation, see README.md

---

**Professional YOLO Annotation Toolkit - v1.0**
