# YOLO DataOps Professional Annotation Toolkit

A professional-grade annotation tool for creating YOLO-format datasets with advanced features for computer vision applications.

## Features

### 🎯 Annotation Mode
- **Intuitive Drawing**: Click and drag to create bounding boxes
- **Multi-class Support**: Assign class IDs (0-9) to each box
- **Smart Zoom**: Zoom in/out centered on cursor position for precise annotations
- **Brightness & Contrast**: Real-time image enhancement with sliders
- **Pan Control**: Arrow keys for image navigation
- **Undo/Redo**: Full history support (U/Y keys)
- **Batch Processing**: Annotate multiple images in one session
- **Visual Feedback**: Real-time crosshair cursor and box information

### 📋 Review Mode
- Review existing YOLO format annotations
- Modify class IDs for existing boxes
- Delete incorrect annotations
- Save updated labels

### 🎨 Visualization Mode
- Generate annotated images with boxes drawn
- Quick verification of annotation quality
- Export for documentation and review

## Installation

### Requirements
- Python 3.9+
- OpenCV (cv2)
- NumPy
- Matplotlib

### Setup
```bash
pip install numpy opencv-python matplotlib
```

## Usage

### Annotate New Images
```bash
python src/yolo_manager.py annotate --img_dir data/images --save_dir data/annotated_labels
```

### Review Existing Annotations
```bash
python src/yolo_manager.py review --img_dir data/images --lbl_dir data/labels --save_dir data/updated_labels
```

### Visualize Annotations
```bash
python src/yolo_manager.py visualize --img_dir data/images --lbl_dir data/labels --save_dir data/visualizations
```

## Keyboard Controls

### Drawing & Selection
| Key | Action |
|-----|--------|
| **Click & Drag** | Draw bounding box |
| **Right Click** | Select/deselect box |
| **0-9** | Set class ID |

### Editing
| Key | Action |
|-----|--------|
| **X** | Delete selected box |
| **C** | Clear all boxes |
| **U** | Undo last action |
| **Y** | Redo last action |

### Zoom & Pan
| Key | Action |
|-----|--------|
| **+/-** | Zoom in/out (centered on cursor) |
| **Arrow Keys** | Pan image |
| **Shift + Arrow** | Move selected box |
| **R** | Reset zoom/pan/brightness |

### Image Adjustments
| Control | Action |
|---------|--------|
| **Brightness Slider** | Adjust brightness (-50 to +50) |
| **Contrast Slider** | Adjust contrast (0.1x to 3.0x) |

### Navigation
| Key | Action |
|-----|--------|
| **Q** | Save and move to next image |

## Output Format

Annotations are saved in YOLO format (one file per image):
```
<class_id> <x_center> <y_center> <width> <height>
```

Where coordinates are normalized to 0-1 range.

Example:
```
0 0.5234 0.3456 0.2341 0.4567
1 0.7234 0.6543 0.1567 0.2341
```

## Project Structure

```
YOLO-DataOps-Toolkit/
├── src/
│   └── yolo_manager.py          # Main annotation tool
├── data/
│   ├── images/                  # Input images
│   ├── annotated_labels/        # Generated labels
│   ├── visualizations/          # Generated visualizations
│   └── updated_labels/          # Updated labels from review mode
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```

## Tips for Best Results

1. **Use Zoom**: Zoom in (+) for precise annotation of small objects
2. **Use Brightness/Contrast**: Adjust lighting for better visibility
3. **Review Often**: Use visualization mode to verify quality
4. **Batch Processing**: Process multiple images efficiently
5. **Undo/Redo**: Don't fear mistakes - use U/Y keys

## Supported Formats

- PNG (default)
- JPG
- Other OpenCV-supported formats (use --format flag)

## Performance

- Handles high-resolution images efficiently
- Real-time zoom and pan operations
- Smooth annotation workflow

## Professional Features

✅ State management with undo/redo
✅ Batch processing
✅ Quality visualization
✅ Professional UI with keyboard shortcuts
✅ Cursor-based zoom
✅ Image enhancement
✅ Multi-class support
✅ YOLO format compliance

## License

MIT License - Feel free to use and modify for your projects

## Support

For issues or feature requests, please create an issue in the repository.

---

**Version**: 1.0 Professional Edition
**Last Updated**: January 2026
