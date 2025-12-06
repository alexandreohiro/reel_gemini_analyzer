import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from reel_analyzer.download.ytdlp import Downloader
from reel_analyzer.video.frames import extract_frames, save_frames
from reel_analyzer.ocr.tesseract import OCRConfig, ocr_frames
from reel_analyzer.gemini.analyzer import GeminiAnalyzer, GeminiConfig

log = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    frames: int = 12
    every_seconds: Optional[float] = None
    scene_detect: bool = False
    vision: bool = False

    # OCR (Tesseract)
    ocr_langs: str = "por+eng"
    tesseract_cmd: Optional[str] = None

    # NOVO: manda o MP4 pro Gemini (transcrição + texto visível)
    gemini_video: bool = True

    out_dir: str = "results"
    frames_dir: str = "frames"
    downloads_dir: str = "downloads"
    acknowledge_rights: bool = False

def run_pipeline(
    *,
    video_path: Optional[str] = None,
    url: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    cfg: Optional[PipelineConfig] = None,
) -> Dict[str, Any]:
    cfg = cfg or PipelineConfig()
    os.makedirs(cfg.out_dir, exist_ok=True)

    # 1) obter vídeo
    info = {}
    if url:
        dl = Downloader(download_dir=cfg.downloads_dir)
        res = dl.download(url, acknowledge_rights=cfg.acknowledge_rights)
        video_path = res.video_path
        info = res.info or {}

    if not video_path:
        raise ValueError("Passe --video (arquivo local) ou --url (com --i-own-this).")

    # 2) frames
    frames, vmeta = extract_frames(
        video_path,
        every_seconds=cfg.every_seconds,
        max_frames=cfg.frames,
        scene_detect=cfg.scene_detect,
    )
    frames_saved = save_frames(frames, os.path.join(cfg.out_dir, cfg.frames_dir))

    # 3) OCR
    ocr_cfg = OCRConfig(langs=cfg.ocr_langs, tesseract_cmd=cfg.tesseract_cmd)
    frames_as_dict = [{"t_sec": fr.t_sec, "image": fr.image, "path": fr.path} for fr in frames_saved]
    ocr = ocr_frames(frames_as_dict, ocr_cfg)

    # 4) Gemini
    ga = GeminiAnalyzer(api_key=gemini_api_key, cfg=GeminiConfig())

    # 4a) NOVO: extrair do vídeo (áudio + texto visível)
    video_extraction = None
    if cfg.gemini_video:
        video_extraction = ga.extract_from_video(video_path, extra_instructions=extra_instructions)

    # 4b) juntar tudo e pedir análise
    parts = []
    if ocr.get("consolidated_text"):
        parts.append("== OCR (Tesseract) ==\n" + ocr["consolidated_text"])

    if video_extraction and video_extraction.get("ok") and video_extraction.get("parsed"):
        ve = video_extraction["parsed"]
        if ve.get("on_screen_text"):
            parts.append("== Texto visível (Gemini/Vídeo) ==\n" + ve["on_screen_text"])
        if ve.get("audio_transcript"):
            parts.append("== Transcrição (Áudio) ==\n" + ve["audio_transcript"])

    consolidated_for_analysis = "\n\n".join(parts).strip()
    text_analysis = ga.analyze_text(consolidated_for_analysis, extra_instructions=extra_instructions)

    vision_analysis = None
    if cfg.vision:
        import pathlib
        image_bytes = []
        for fr in frames_saved[: min(8, len(frames_saved))]:
            if fr.path and os.path.exists(fr.path):
                image_bytes.append(pathlib.Path(fr.path).read_bytes())
        vprompt = (
            "Analise estes frames de um vídeo curto.\n"
            "1) descreva o que aparece visualmente\n"
            "2) extraia texto visível na cena\n"
            "3) diga o tema provável e por quê\n"
            "Responda em PT-BR."
        )
        vision_analysis = ga.analyze_vision(vprompt, image_bytes)

    result = {
        "input": {"video_path": video_path, "url": url},
        "video_meta": vmeta,
        "download_info": {
            "id": info.get("id"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "webpage_url": info.get("webpage_url"),
        } if info else {},
        "frames": [{"index": fr.index, "t_sec": fr.t_sec, "path": fr.path} for fr in frames_saved],
        "ocr": ocr,
        "gemini": {
            "video_extraction": video_extraction,
            "text_analysis": text_analysis,
            "vision_analysis": vision_analysis,
        },
    }
    return result

def save_json(result: Dict[str, Any], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
