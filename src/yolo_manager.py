import numpy as np
import cv2
import time
import os
from glob import glob
from matplotlib import pyplot as plt
import shutil
import argparse
import json
from pathlib import Path

class AnnotationState:
    """Manages state and history for professional annotation"""
    def __init__(self):
        self.rectangles = []
        self.history = []
        self.history_index = -1
        self.selected = None
        self.brightness = 50
        self.contrast = 10
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.current_class = 0
        self.drawing = False
        
    def save_state(self):
        """Save current state to history"""
        state = {
            'rectangles': [list(r) for r in self.rectangles],
            'brightness': self.brightness,
            'contrast': self.contrast,
            'zoom': self.zoom_factor,
            'pan': (self.pan_x, self.pan_y)
        }
        self.history_index += 1
        self.history = self.history[:self.history_index]
        self.history.append(state)
        
    def undo(self):
        """Undo last action"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index])
            
    def redo(self):
        """Redo last undone action"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index])
            
    def restore_state(self, state):
        """Restore state from history"""
        self.rectangles = [tuple(r) for r in state['rectangles']]
        self.brightness = state['brightness']
        self.contrast = state['contrast']
        self.zoom_factor = state['zoom']
        self.pan_x, self.pan_y = state['pan']

class YOLOUtility:
    """Utility class for bounding boxes and OpenCV operations"""
    
    @staticmethod
    def draw_rectangle(event, x, y, flags, state):
        """Professional mouse callback with zoom support"""
        state.mouse_x = x
        state.mouse_y = y
        
        if event == cv2.EVENT_LBUTTONDOWN:
            state.drawing = True
            state.save_state()
            state.rectangles.append((np.float32(state.current_class), x, y, x, y))
        elif event == cv2.EVENT_MOUSEMOVE:
            if state.drawing and len(state.rectangles) > 0:
                r = state.rectangles[-1]
                state.rectangles[-1] = (r[0], r[1], r[2], x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            state.drawing = False
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Right click to select box
            for idx in range(len(state.rectangles) - 1, -1, -1):
                _, x1, y1, x2, y2 = state.rectangles[idx]
                if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
                    state.selected = idx
                    break

    @staticmethod
    def normBboxes(rectangles, imgShape):
        """Normalize bounding boxes"""
        bboxes = np.zeros_like(rectangles, dtype=float)
        bboxes[:,2] = (rectangles[:,2] - rectangles[:,0]) / imgShape[1]
        bboxes[:,3] = (rectangles[:,3] - rectangles[:,1]) / imgShape[0]
        bboxes[:,0] = rectangles[:,0] / imgShape[1] + 0.5*bboxes[:,2]
        bboxes[:,1] = rectangles[:,1] / imgShape[0] + 0.5*bboxes[:,3]
        return bboxes

    @staticmethod
    def deNormBboxes(bboxes, image_width, image_height):
        """Denormalize bounding boxes"""
        bboxes[:,0] = (bboxes[:,0] - 0.5*bboxes[:,2]) * image_width
        bboxes[:,1] = (bboxes[:,1] - 0.5*bboxes[:,3]) * image_height
        bboxes[:,2] = bboxes[:,0] + bboxes[:,2] * image_width
        bboxes[:,3] = bboxes[:,1] + bboxes[:,3] * image_height
        return np.array(bboxes, dtype=int)
    
    @staticmethod
    def apply_enhancements(img, brightness, contrast, zoom_factor, pan_x, pan_y, mouse_x, mouse_y):
        """Apply brightness, contrast, zoom, and pan - returns enhanced image and transformation info"""
        # Apply brightness and contrast
        enhanced = cv2.convertScaleAbs(img, alpha=contrast/10.0, beta=brightness-50)
        
        # Store transformation info for rectangle mapping
        transform_info = {'zoom': zoom_factor, 'pan_x': pan_x, 'pan_y': pan_y, 'mouse_x': mouse_x, 'mouse_y': mouse_y, 'img_h': enhanced.shape[0], 'img_w': enhanced.shape[1]}
        
        # Apply zoom to cursor position - but keep rectangles in original coords
        if zoom_factor != 1.0:
            h, w = enhanced.shape[:2]
            zoom_h, zoom_w = int(h / zoom_factor), int(w / zoom_factor)
            center_y = mouse_y + pan_y
            center_x = mouse_x + pan_x
            
            y1 = max(0, center_y - zoom_h // 2)
            y2 = min(h, center_y + zoom_h // 2)
            x1 = max(0, center_x - zoom_w // 2)
            x2 = min(w, center_x + zoom_w // 2)
            
            cropped = enhanced[y1:y2, x1:x2]
            if cropped.size > 0:
                enhanced = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
                # Store crop region for transformation
                transform_info['crop_y1'] = y1
                transform_info['crop_y2'] = y2
                transform_info['crop_x1'] = x1
                transform_info['crop_x2'] = x2
        
        return enhanced, transform_info
    
    @staticmethod
    def transform_rect_for_display(rect, transform_info, original_h, original_w):
        """Transform rectangle coordinates from original to display space"""
        _, x1, y1, x2, y2 = rect
        
        # If no zoom, return as is
        if transform_info['zoom'] == 1.0:
            return (_, int(x1), int(y1), int(x2), int(y2))
        
        # Apply reverse transformation (from original coords to zoomed/displayed coords)
        img_h = transform_info['img_h']
        img_w = transform_info['img_w']
        crop_y1 = transform_info.get('crop_y1', 0)
        crop_y2 = transform_info.get('crop_y2', img_h)
        crop_x1 = transform_info.get('crop_x1', 0)
        crop_x2 = transform_info.get('crop_x2', img_w)
        
        crop_h = crop_y2 - crop_y1
        crop_w = crop_x2 - crop_x1
        
        # Scale from original coords to cropped space
        x1_disp = ((x1 - crop_x1) / crop_w * img_w) if crop_w > 0 else x1
        y1_disp = ((y1 - crop_y1) / crop_h * img_h) if crop_h > 0 else y1
        x2_disp = ((x2 - crop_x1) / crop_w * img_w) if crop_w > 0 else x2
        y2_disp = ((y2 - crop_y1) / crop_h * img_h) if crop_h > 0 else y2
        
        return (_, int(x1_disp), int(y1_disp), int(x2_disp), int(y2_disp))
    
    @staticmethod
    def drawBoxes(image_path: str, normalised=True, max_width: int = 1680, max_height: int = 1050):
        """Professional annotation interface with full features"""
        state = AnnotationState()
        
        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"Error: Could not read image {image_path}")
            return np.array([])

        # Resize if needed
        scale_factor = 1
        if original_image.shape[1] > max_width or original_image.shape[0] > max_height:
            scale_factor = min(max_width / original_image.shape[1], max_height / original_image.shape[0])
            original_image = cv2.resize(original_image, None, fx=scale_factor, fy=scale_factor)

        image_copy = original_image.copy()
        windowName = "YOLO Annotation Tool - Professional Edition"
        
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(windowName, int(image_copy.shape[1]*0.8), int(image_copy.shape[0]*0.8))
        cv2.setMouseCallback(windowName, YOLOUtility.draw_rectangle, state)
        
        # Create trackbars
        cv2.createTrackbar('Brightness', windowName, state.brightness, 100, lambda x: None)
        cv2.createTrackbar('Contrast', windowName, state.contrast, 30, lambda x: None)
        
        state.save_state()
        
        print(f"\nAnnotating: {os.path.basename(image_path)}")
        
        while True:
            # Update state from trackbars
            state.brightness = cv2.getTrackbarPos('Brightness', windowName)
            state.contrast = cv2.getTrackbarPos('Contrast', windowName)
            
            # Apply enhancements
            display_img, transform_info = YOLOUtility.apply_enhancements(
                image_copy.copy(), 
                state.brightness, 
                state.contrast, 
                state.zoom_factor, 
                state.pan_x, 
                state.pan_y,
                state.mouse_x,
                state.mouse_y
            )
            
            # Draw rectangles with proper coordinate transformation
            for index, rect in enumerate(state.rectangles):
                _, x1, y1, x2, y2 = YOLOUtility.transform_rect_for_display(rect, transform_info, image_copy.shape[0], image_copy.shape[1])
                color = (0, 0, 255) if state.selected == index else (0, 255, 0)
                thickness = 3 if state.selected == index else 2
                cv2.rectangle(display_img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
                cv2.putText(display_img, str(int(_)), (int(x1), int(y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw cursor crosshair
            cv2.line(display_img, (state.mouse_x-10, state.mouse_y), (state.mouse_x+10, state.mouse_y), (255, 0, 0), 1)
            cv2.line(display_img, (state.mouse_x, state.mouse_y-10), (state.mouse_x, state.mouse_y+10), (255, 0, 0), 1)
            
            # Draw UI information
            y_offset = 25
            info_lines = [
                f"Image: {os.path.basename(image_path)} | Boxes: {len(state.rectangles)} | Class: {state.current_class}",
                f"Zoom: {state.zoom_factor:.1f}x | Brightness: {state.brightness-50:+d} | Contrast: {state.contrast/10:.1f}x",
                "DRAW: Click-drag | SELECT: Right-click box | MOVE: Arrow keys | PAN: SHIFT+Arrow",
                "ZOOM: +/- | BRIGHTNESS/CONTRAST: Sliders | CLASS: 0-9 | DELETE: X | UNDO: U | REDO: Y",
                "RESET: R | CLEAR ALL: C | QUIT: Q"
            ]
            for i, line in enumerate(info_lines):
                cv2.putText(display_img, line, (10, y_offset + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            cv2.imshow(windowName, display_img)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'): 
                break
            elif key == ord('x'):  # Delete selected
                if state.selected is not None and len(state.rectangles) > 0:
                    state.save_state()
                    state.rectangles.pop(state.selected)
                    state.selected = None if not state.rectangles else min(state.selected, len(state.rectangles)-1)
            elif key == ord('c'):  # Clear all
                if len(state.rectangles) > 0:
                    state.save_state()
                    state.rectangles.clear()
                    state.selected = None
            elif key == ord('+') or key == ord('='):  # Zoom in
                state.zoom_factor = min(5.0, state.zoom_factor * 1.2)
            elif key == ord('-'):  # Zoom out
                state.zoom_factor = max(0.2, state.zoom_factor / 1.2)
            elif key == ord('r'):  # Reset
                state.zoom_factor = 1.0
                state.pan_x, state.pan_y = 0, 0
                cv2.setTrackbarPos('Brightness', windowName, 50)
                cv2.setTrackbarPos('Contrast', windowName, 10)
            elif key == ord('u'):  # Undo
                state.undo()
            elif key == ord('y'):  # Redo
                state.redo()
            elif key == 81:  # Left arrow
                state.pan_x -= 20
            elif key == 83:  # Right arrow
                state.pan_x += 20
            elif key == 82:  # Up arrow
                state.pan_y -= 20
            elif key == 84:  # Down arrow
                state.pan_y += 20
            elif key in [ord(str(k)) for k in range(10)]:  # Class selection
                state.current_class = chr(key)
            elif key == 255:  # No key pressed
                pass

        cv2.destroyAllWindows()
        bboxes = np.asarray(state.rectangles)
        if len(bboxes) > 0:
            bboxes[:,1:] = YOLOUtility.normBboxes(bboxes[:,1:], image_copy.shape)
            return bboxes
        else: 
            return np.array([])

class YOLOManager:
    """Professional YOLO dataset management"""
    def __init__(self, imgDir, lblDir, imgFormat='png'):
        self.imgFormat = imgFormat
        self.imgList = sorted(glob(os.path.join(imgDir, '*.' + imgFormat)))
        self.lblDir = lblDir
        self.dataList = []
        
        if not os.path.exists(lblDir):
            os.makedirs(lblDir)

        for imgPath in self.imgList:
            lblPath = os.path.join(lblDir, os.path.basename(imgPath).replace('.'+imgFormat, '.txt'))
            self.dataList.append((imgPath, lblPath))

        print(f'\n✓ Found {len(self.imgList)} images in {imgDir}')

    def annotateImages(self, saveDir):
        """Annotate all images with professional tool"""
        if not os.path.exists(saveDir): 
            os.makedirs(saveDir)
        
        total = len(self.imgList)
        for idx, path in enumerate(self.imgList):
            print(f"\n[{idx+1}/{total}] Processing: {os.path.basename(path)}")
            bboxes = YOLOUtility.drawBoxes(path, normalised=True)
            if bboxes.size > 0:
                lblPath = os.path.join(saveDir, os.path.basename(path).replace('.'+self.imgFormat, '.txt'))
                np.savetxt(lblPath, bboxes, fmt='%i %1.6f %1.6f %1.6f %1.6f', delimiter=' ')
                print(f"✓ Saved {len(bboxes)} boxes to {os.path.basename(lblPath)}")
            else:
                print(f"⊘ No boxes annotated")

    def reviewLabels(self, saveDir):
        """Review and edit existing labels"""
        if not os.path.exists(saveDir): 
            os.makedirs(saveDir)
        
        total = len(self.dataList)
        for i, (imgPath, lblPath) in enumerate(self.dataList):
            if not os.path.exists(lblPath): 
                continue
            
            print(f"\n[{i+1}/{total}] Reviewing: {os.path.basename(imgPath)}")
            img = cv2.imread(imgPath)
            
            try:
                lblData = np.loadtxt(lblPath).reshape([-1, 5])
            except:
                continue

            if lblData.shape[0] == 0: 
                continue

            # Convert to pixel coords
            lbl_pixels = np.hstack([lblData[:, :1].copy(), YOLOUtility.deNormBboxes(lblData[:, 1:].copy(), *img.shape[:2][::-1])])
            
            # Display with options
            for box_idx, box in enumerate(lbl_pixels):
                cid, x0, y0, x1, y1 = box
                temp_img = img.copy()
                cv2.rectangle(temp_img, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 3)
                cv2.putText(temp_img, f"Box {box_idx+1}/{len(lbl_pixels)} | Class: {int(cid)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Review Labels", temp_img)
                key = cv2.waitKey(0) & 0xFF
                if key == ord('d'):  # Delete
                    lblData[box_idx] = np.nan
                elif key in [ord(str(k)) for k in range(10)]:  # Change class
                    lblData[box_idx, 0] = int(chr(key))
            
            cv2.destroyAllWindows()
            
            # Save updated labels
            new_labels = lblData[~np.isnan(lblData).any(axis=1), :]
            savePath = os.path.join(saveDir, os.path.basename(lblPath))
            if len(new_labels) > 0:
                np.savetxt(savePath, new_labels, fmt='%i %1.6f %1.6f %1.6f %1.6f', delimiter=' ')
            print(f"✓ Updated labels saved")

    def visualizeDataset(self, saveDir):
        """Visualize annotations"""
        if not os.path.exists(saveDir): 
            os.makedirs(saveDir)
        
        total = len(self.dataList)
        for idx, (imgPath, lblPath) in enumerate(self.dataList):
            if not os.path.exists(lblPath): 
                continue
            
            img = cv2.imread(imgPath)
            try:
                lbl = np.loadtxt(lblPath).reshape([-1, 5])
            except: 
                continue
            
            print(f"[{idx+1}/{total}] Visualizing: {os.path.basename(imgPath)}")
            
            for box in lbl:
                x0, y0 = (box[1]-0.5*box[3])*img.shape[1], (box[2]-0.5*box[4])*img.shape[0]
                x1, y1 = x0 + box[3]*img.shape[1], y0 + box[4]*img.shape[0]
                cv2.rectangle(img, (int(x0),int(y0)), (int(x1), int(y1)), (0,255,0), 2)
                cv2.putText(img, str(int(box[0])), (int(x0),int(y0)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            
            cv2.imwrite(os.path.join(saveDir, 'vis_' + os.path.basename(imgPath)), img)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO DataOps Professional Annotation Toolkit")
    parser.add_argument('mode', choices=['annotate', 'review', 'visualize'], help="Operation mode")
    parser.add_argument('--img_dir', required=True, help="Path to image directory")
    parser.add_argument('--lbl_dir', help="Path to label directory")
    parser.add_argument('--save_dir', help="Path to save output")
    parser.add_argument('--format', default='png', help="Image format")

    args = parser.parse_args()
    
    lbl_dir = args.lbl_dir if args.lbl_dir else args.img_dir
    save_dir = args.save_dir if args.save_dir else args.img_dir

    print("\n" + "="*70)
    print(" YOLO DataOps Professional Annotation Toolkit")
    print("="*70)

    manager = YOLOManager(args.img_dir, lbl_dir, args.format)

    if args.mode == 'annotate':
        print("\n✓ ANNOTATION MODE - Draw bounding boxes on images")
        print("="*70)
        manager.annotateImages(save_dir)
    elif args.mode == 'review':
        print("\n✓ REVIEW MODE - Edit existing annotations")
        print("="*70)
        manager.reviewLabels(save_dir)
    elif args.mode == 'visualize':
        print("\n✓ VISUALIZATION MODE - Generate annotated images")
        print("="*70)
        manager.visualizeDataset(save_dir)
    
    print("\n✓ Completed successfully!")
    print("="*70 + "\n")
