import cv2
import numpy as np
import os
from abc import ABC, abstractmethod
from nudenet import NudeDetector
from PIL import Image

try:
    from transformers import pipeline
    import torch
except ImportError:
    pipeline = None

# All sensitive body part labels from NudeNet v3
SENSITIVE_LABELS = {
    'FEMALE_GENITALIA_EXPOSED',
    'FEMALE_BREAST_EXPOSED',
    'BUTTOCKS_EXPOSED',
    'ANUS_EXPOSED',
    'MALE_GENITALIA_EXPOSED',
    'FEMALE_BREAST_COVERED',
    'BUTTOCKS_COVERED',
    'FEMALE_GENITALIA_COVERED',
    'MALE_GENITALIA_COVERED',
    'BELLY_EXPOSED',
}


def read_image(path: str):
    """
    Robust image reader. Tries 3 methods in order:
    1. cv2.imread (fastest)
    2. PIL Image → numpy (handles webp, gif, etc.)
    3. Read raw bytes → cv2.imdecode (bypasses extension mismatches)
    Returns a BGR numpy array or None.
    """
    # Method 1: OpenCV direct read
    img = cv2.imread(str(path))
    if img is not None:
        return img

    # Method 2: Pillow fallback
    try:
        pil_img = Image.open(str(path)).convert('RGB')
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        pass

    # Method 3: Raw byte decode (handles files with wrong extensions)
    try:
        with open(str(path), 'rb') as f:
            raw = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except Exception:
        pass

    return None


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, image_path: str):
        pass


class LocalNudeNetDetector(BaseDetector):
    def __init__(self):
        self.detector = NudeDetector()

    def detect(self, image_path: str, use_deep_scan: bool = True):
        img = read_image(image_path)
        if img is None:
            print(f"[Detector] Warning: Cannot read '{image_path}', skipping detection.")
            return []

        h, w = img.shape[:2]
        all_results = list(self.detector.detect(image_path))

        # Deep Scan: 3x3 overlapping tile grid for small area detection
        if use_deep_scan and w > 100 and h > 100:
            tile_w = w // 2
            tile_h = h // 2
            x_coords = [0, w // 4, w // 2]
            y_coords = [0, h // 4, h // 2]

            tile_path = f"_tile_{os.getpid()}.png"
            try:
                for y_start in y_coords:
                    for x_start in x_coords:
                        x2 = min(w, x_start + tile_w)
                        y2 = min(h, y_start + tile_h)
                        tile = img[y_start:y2, x_start:x2]
                        if tile.size == 0:
                            continue

                        cv2.imwrite(tile_path, tile)
                        for res in self.detector.detect(tile_path):
                            bx, by, bw, bh = res['box']
                            res['box'] = [bx + x_start, by + y_start, bw, bh]
                            all_results.append(res)
            finally:
                if os.path.exists(tile_path):
                    os.remove(tile_path)

        normalized = [
            {
                'box': res['box'],
                'score': float(res['score']),
                'label': res.get('class', res.get('label', 'unknown'))
            }
            for res in all_results
        ]
        return self._apply_nms(normalized)

    def _apply_nms(self, detections, iou_threshold=0.4):
        if not detections:
            return []
        detections = sorted(detections, key=lambda x: x['score'], reverse=True)
        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)
            detections = [
                d for d in detections
                if d['label'] != best['label'] or self._iou(d['box'], best['box']) < iou_threshold
            ]
        return keep

    def _iou(self, a, b):
        xa = max(a[0], b[0])
        ya = max(a[1], b[1])
        xb = min(a[0] + a[2], b[0] + b[2])
        yb = min(a[1] + a[3], b[1] + b[3])
        inter = max(0, xb - xa) * max(0, yb - ya)
        union = a[2] * a[3] + b[2] * b[3] - inter
        return inter / (union + 1e-10)


class LocalNSFWClassifier:
    def __init__(self):
        self.classifier = None
        if pipeline is None:
            return
        try:
            self.classifier = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
        except Exception as e:
            print(f"[Classifier] Failed to load: {e}")

    def classify(self, image_path: str):
        if not self.classifier:
            return []
        try:
            results = self.classifier(image_path)
            return [{"label": r["label"], "score": float(r["score"])} for r in results]
        except Exception as e:
            print(f"[Classifier] Error on '{image_path}': {e}")
            return []


class ImageProcessor:
    def __init__(self, blur_radius: int = 91):
        self.blur_radius = blur_radius

    def process(self, image_path: str, detections: list, output_path: str,
                mode: str = "blur", nsfw_scores: list = None, color_hex: str = "#000000"):
        img = read_image(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: '{image_path}'")

        h_img, w_img = img.shape[:2]

        # Determine risk level from classifier scores
        # normal_score: how confident we are the image is clean
        normal_score = next((s['score'] for s in (nsfw_scores or []) if s['label'].lower() == 'normal'), 0.0)
        
        # is_high_risk: classifier is VERY confident it's NSFW (>60%)
        is_high_risk = any(
            s['label'].lower() in {'porn', 'hentai', 'nsfw', 'unsafe'} and s['score'] > 0.60
            for s in (nsfw_scores or [])
        )

        # Parse hex color → BGR
        hex_clean = color_hex.lstrip('#')
        rgb = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
        bgr_color = (rgb[2], rgb[1], rgb[0])

        # Define label groups for localized sensitivity
        EXPOSED_LABELS = {
            'FEMALE_GENITALIA_EXPOSED', 'FEMALE_BREAST_EXPOSED', 
            'BUTTOCKS_EXPOSED', 'ANUS_EXPOSED', 'MALE_GENITALIA_EXPOSED'
        }
        COVERED_OR_MINOR = {
            'FEMALE_BREAST_COVERED', 'BUTTOCKS_COVERED', 'FEMALE_GENITALIA_COVERED', 
            'MALE_GENITALIA_COVERED', 'BELLY_EXPOSED'
        }

        applied_count = 0
        for det in detections:
            label = det['label']
            score = det['score']

            if label not in SENSITIVE_LABELS:
                continue

            # Logic Adjustment for "Normal" Confident images:
            # 1. If Normal Confidence > 90%, only blur EXPOSED genitalia/breasts if score is very high (>=80%)
            #    Completely ignore COVERED areas or BELLY.
            if normal_score > 0.90:
                if label in COVERED_OR_MINOR:
                    continue
                if label in EXPOSED_LABELS and score < 0.80:
                    continue
            
            # 2. If Normal Confidence > 70%, be very strict
            elif normal_score > 0.70:
                if label in COVERED_OR_MINOR and score < 0.75:
                    continue
                if label in EXPOSED_LABELS and score < 0.60:
                    continue

            # 3. Default catch-all thresholds
            else:
                threshold = 0.30 if is_high_risk else 0.55
                if score < threshold:
                    continue

            x, y, w, h = map(int, det['box'])
            padding = 40 if is_high_risk else 10
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w_img, x + w + padding)
            y2 = min(h_img, y + h + padding)

            if x2 <= x1 or y2 <= y1:
                continue

            roi = img[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            if mode == "pixel":
                h_roi, w_roi = roi.shape[:2]
                divisor = max(4, self.blur_radius // 4)
                if is_high_risk:
                    divisor = int(divisor * 1.3)
                nw = max(1, w_roi // divisor)
                nh = max(1, h_roi // divisor)
                temp = cv2.resize(roi, (nw, nh), interpolation=cv2.INTER_LINEAR)
                processed_roi = cv2.resize(temp, (w_roi, h_roi), interpolation=cv2.INTER_NEAREST)
            elif mode == "solid":
                processed_roi = np.full_like(roi, bgr_color)
            else:  # blur (default)
                r = self.blur_radius if self.blur_radius % 2 != 0 else self.blur_radius + 1
                processed_roi = cv2.GaussianBlur(roi, (r, r), 0)

            img[y1:y2, x1:x2] = processed_roi
            applied_count += 1

        cv2.imwrite(output_path, img)
        return output_path, applied_count
