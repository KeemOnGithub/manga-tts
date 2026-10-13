import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Dict

def extract_panels_from_page(page_image: np.ndarray, page_num: int) -> List[Tuple[int, np.ndarray]]:
    """
    Extract individual panels from a page using contour detection.
    Returns list of (panel_index, panel_image) tuples.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)
    
    # Apply binary threshold
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and sort contours by area (largest panels first)
    valid_contours = []
    min_area = page_image.shape[0] * page_image.shape[1] * 0.01  # at least 1% of page
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            valid_contours.append((y, x, w, h))  # Store y-first for top-to-bottom sorting
    
    # Sort by vertical position (top to bottom), then horizontal (left to right)
    valid_contours.sort(key=lambda c: (c[0], c[1]))
    
    # Extract panel images
    panels = []
    for idx, (y, x, w, h) in enumerate(valid_contours, start=1):
        panel_img = page_image[y:y+h, x:x+w]
        panels.append((idx, panel_img))
    
    return panels


def save_panel(panel_image: np.ndarray, page_num: int, panel_num: int, temp_dir: Path) -> Path:
    """Save panel image to temp directory"""
    filename = f"page_{page_num:02d}_panel_{panel_num:03d}.png"
    filepath = temp_dir / filename
    
    # Convert BGR to RGB if needed
    if len(panel_image.shape) == 3:
        panel_image = cv2.cvtColor(panel_image, cv2.COLOR_BGR2RGB)
    
    Image.fromarray(panel_image).save(filepath)
    return filepath

if __name__ == "__main__":
    # Example usage
    page_image = cv2.imread("./img/04.png")
    panels = extract_panels_from_page(page_image, page_num=1)
    
    temp_dir = Path("temp_panels")
    temp_dir.mkdir(exist_ok=True)
    
    for panel_num, panel_img in panels:
        save_panel(panel_img, page_num=1, panel_num=panel_num, temp_dir=temp_dir)
