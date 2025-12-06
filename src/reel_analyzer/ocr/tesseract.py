import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np
import cv2
from PIL import Image
import pytesseract

from reel_analyzer.utils.text import normalize_text, dedupe_lines

log = logging.getLogger(__name__)

@dataclass
class OCRConfig:
    langs: str = "por+eng"
    psm: int = 6
    oem: int = 3
    tesseract_cmd: Optional[str] = None
    max_width: int = 1200

def _preprocess(img: Image.Image, max_width: int) -> Image.Image:
    w, h = img.size
    if w > max_width:
        nh = int(h * (max_width / w))
        img = img.resize((max_width, nh))

    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    gray = cv2.bilateralFilter(gray, 7, 50, 50)

    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 9
    )
    return Image.fromarray(thr)

def ocr_frames(frames: List[Dict], cfg: OCRConfig) -> Dict:
    if cfg.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd

    all_text = []
    frame_texts = []
    config = f"--psm {cfg.psm} --oem {cfg.oem}"

    for i, fr in enumerate(frames):
        img = fr["image"] if isinstance(fr, dict) else getattr(fr, "image")
        try:
            prep = _preprocess(img, cfg.max_width)
            txt = pytesseract.image_to_string(prep, lang=cfg.langs, config=config)
            txt = normalize_text(txt)
            if txt:
                frame_texts.append({"frame": i, "t_sec": fr.get("t_sec"), "text": txt})
                all_text.append(txt)
        except Exception as e:
            log.warning("OCR falhou no frame %d: %s", i, e)

    lines = []
    for block in all_text:
        lines.extend([ln for ln in block.splitlines() if ln.strip()])
    consolidated = "\n".join(dedupe_lines(lines))

    return {
        "langs": cfg.langs,
        "total_frames": len(frames),
        "frames_with_text": len(frame_texts),
        "frame_texts": frame_texts,
        "consolidated_text": consolidated,
    }
