"""
Converts a photo into a cartoon-style avatar using OpenCV.
Output: jordi_cartoon.png (used by default in videocall mode)

Usage:
  python3 07_cartoon_avatar.py
  python3 07_cartoon_avatar.py --input my_photo.jpg --output my_cartoon.png
"""

import cv2
import numpy as np
import argparse
import os

def cartoonize(img: np.ndarray) -> np.ndarray:
    """
    Multi-step cartoon effect:
    1. Bilateral filter to smooth while preserving edges
    2. Adaptive edge detection
    3. Color quantization via repeated bilateral filtering
    4. Combine edges with quantized colors
    """
    h, w = img.shape[:2]

    # Step 1: Repeated bilateral filter for painting-like smoothness
    smooth = img.copy()
    for _ in range(4):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)

    # Step 2: Edge detection on grayscale
    gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.medianBlur(gray, 7)
    edges     = cv2.adaptiveThreshold(
        gray_blur, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=9,
        C=4
    )
    # Dilate edges slightly for a bolder cartoon look
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    edges  = cv2.erode(edges, kernel, iterations=1)

    # Step 3: Color quantization (k-means, 12 colors)
    data     = smooth.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(data, 12, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS)
    quantized = centers[labels.flatten()].reshape(smooth.shape).astype(np.uint8)

    # Step 4: Apply edge mask
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cartoon   = cv2.bitwise_and(quantized, edges_bgr)

    # Step 5: Slight saturation boost for vivid cartoon look
    hsv = cv2.cvtColor(cartoon, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.4, 0, 255)
    cartoon = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    return cartoon


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="jordi.jpeg")
    parser.add_argument("--output", default="jordi_cartoon.png")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        return

    print(f"Loading {args.input}...")
    img = cv2.imread(args.input)

    print("Applying cartoon effect...")
    cartoon = cartoonize(img)

    cv2.imwrite(args.output, cartoon)
    print(f"Saved: {args.output}")

    # Show side by side
    h = min(img.shape[0], 600)
    scale   = h / img.shape[0]
    w_shown = int(img.shape[1] * scale)
    left    = cv2.resize(img,     (w_shown, h))
    right   = cv2.resize(cartoon, (w_shown, h))

    # Add labels
    cv2.putText(left,  "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(right, "Cartoon",  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    combined = np.hstack([left, right])
    preview_path = args.output.replace(".png", "_preview.png")
    cv2.imwrite(preview_path, combined)
    print(f"Preview saved: {preview_path}")

    # Show window only if a display is available
    try:
        cv2.imshow("Cartoon Avatar — press any key to close", combined)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception:
        pass


if __name__ == "__main__":
    main()
