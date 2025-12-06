import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

@dataclass
class FrameSample:
    index: int
    t_sec: float
    image: Image.Image
    path: Optional[str] = None

def _video_info(cap: cv2.VideoCapture) -> Tuple[float, int, int, float]:
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = (total_frames / fps) if total_frames and fps else 0.0
    return fps, total_frames, w*h, duration

def extract_frames(
    video_path: str,
    *,
    every_seconds: Optional[float] = None,
    max_frames: int = 12,
    scene_detect: bool = False,
) -> Tuple[List[FrameSample], dict]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Não consegui abrir o vídeo: {video_path}")

    fps, total_frames, _, duration = _video_info(cap)
    meta = {"fps": fps, "total_frames": total_frames, "duration_sec": duration}

    if total_frames <= 0:
        # fallback: lê até acabar, contando
        total_frames = 0
        while True:
            ok, _ = cap.read()
            if not ok:
                break
            total_frames += 1
        cap.release()
        cap = cv2.VideoCapture(video_path)
        meta["total_frames"] = total_frames
        duration = (total_frames / fps) if fps else 0.0
        meta["duration_sec"] = duration

    # estratégia 1: a cada X segundos
    if every_seconds and every_seconds > 0:
        step = max(1, int(round(fps * every_seconds)))
        indices = list(range(0, total_frames, step))[:max_frames]
    else:
        # estratégia 2: espalhar max_frames ao longo do vídeo
        if max_frames <= 1:
            indices = [max(0, total_frames // 2)]
        else:
            indices = np.linspace(0, max(0, total_frames - 1), num=max_frames).astype(int).tolist()

    # estratégia 3 (opcional): scene detect simples por histograma
    if scene_detect and total_frames > 0:
        candidates = []
        prev_hist = None
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        for i in range(total_frames):
            ok, frame = cap.read()
            if not ok:
                break
            if i % max(1, int(fps/2)) != 0:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            if prev_hist is not None:
                diff = float(np.sum(np.abs(hist - prev_hist)))
                candidates.append((diff, i))
            prev_hist = hist
        candidates.sort(reverse=True)
        scene_idxs = [i for _, i in candidates[:max_frames]]
        # mistura com indices espalhados
        indices = sorted(set(indices + scene_idxs))[:max_frames]

    frames: List[FrameSample] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        t_sec = float(idx) / float(fps) if fps else 0.0
        frames.append(FrameSample(index=int(idx), t_sec=t_sec, image=img))

    cap.release()
    log.info("Frames extraídos: %d", len(frames))
    return frames, meta

def save_frames(frames: List[FrameSample], out_dir: str) -> List[FrameSample]:
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for k, fr in enumerate(frames):
        path = os.path.join(out_dir, f"frame_{k:03d}_t{fr.t_sec:.2f}s.jpg")
        fr.image.save(path, format="JPEG", quality=92)
        out.append(FrameSample(index=fr.index, t_sec=fr.t_sec, image=fr.image, path=path))
    return out
