"""
YOLO DataOps Toolkit - Configuration Module
Professional annotation tool for YOLO dataset creation
"""

# Version Information
VERSION = "1.0.0"
EDITION = "Professional"
RELEASE_DATE = "January 2026"

# Default Configuration
DEFAULT_CONFIG = {
    "image_format": "png",
    "max_width": 1680,
    "max_height": 1050,
    "classes": list(range(10)),  # 0-9
    
    # UI Configuration
    "ui": {
        "zoom_speed": 1.2,
        "min_zoom": 0.2,
        "max_zoom": 5.0,
        "brightness_range": (-50, 50),
        "contrast_range": (0.1, 3.0),
        "pan_speed": 20,
    },
    
    # Color Scheme
    "colors": {
        "box_normal": (0, 255, 0),      # Green
        "box_selected": (0, 0, 255),    # Red
        "cursor": (255, 0, 0),          # Blue
        "text": (0, 255, 255),          # Yellow
        "info": (0, 255, 255),          # Yellow
    },
    
    # YOLO Format
    "yolo_format": {
        "extension": ".txt",
        "format_string": "%i %1.6f %1.6f %1.6f %1.6f",
        "delimiter": " ",
        "normalized": True,
    }
}

# Feature Flags
FEATURES = {
    "undo_redo": True,
    "batch_processing": True,
    "image_enhancement": True,
    "cursor_zoom": True,
    "visualization": True,
    "review_mode": True,
}

# Keyboard Shortcuts
SHORTCUTS = {
    "draw_box": "Click & Drag",
    "select_box": "Right Click",
    "delete_box": "X",
    "clear_all": "C",
    "zoom_in": "+",
    "zoom_out": "-",
    "pan_left": "Left Arrow",
    "pan_right": "Right Arrow",
    "pan_up": "Up Arrow",
    "pan_down": "Down Arrow",
    "undo": "U",
    "redo": "Y",
    "reset": "R",
    "set_class": "0-9",
    "save_quit": "Q",
}

# Supported Formats
SUPPORTED_FORMATS = [
    "png", "jpg", "jpeg", "bmp", "tiff", "webp"
]

# Professional Features
PROFESSIONAL_FEATURES = [
    "✓ Advanced Zoom with Cursor Tracking",
    "✓ Real-time Brightness & Contrast Control",
    "✓ Complete Undo/Redo History",
    "✓ Multi-class Annotation Support",
    "✓ Batch Image Processing",
    "✓ Professional UI with Keyboard Shortcuts",
    "✓ Automatic Visualization Generation",
    "✓ Label Review & Editing",
    "✓ YOLO Format Compliance",
    "✓ High-Resolution Image Support",
]

def print_info():
    """Print toolkit information"""
    print("\n" + "="*70)
    print(f" YOLO DataOps Toolkit - {EDITION} Edition v{VERSION}")
    print("="*70)
    print(f"\nRelease Date: {RELEASE_DATE}")
    print("\nFeatures:")
    for feature in PROFESSIONAL_FEATURES:
        print(f"  {feature}")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    print_info()
