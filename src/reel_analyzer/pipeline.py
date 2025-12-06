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
    # vídeo -> frames
    frames: int = 12
    every_seconds: Optional[float] = None
    scene_detect: bool = False

    # OCR
    ocr_langs: str = "por+eng"
    tesseract_cmd: Optional[str] = None

    # ÁUDIO (Whisper)
    use_audio: bool = True
    whisper_model: str = "small"
    whisper_language: Optional[str] = "pt"   # None = auto
    whisper_device: str = "cpu"              # "cuda" se tiver GPU

    # Gemini
    vision: bool = False

    # paths
    out_dir: str = "results"
    frames_dir: str = "frames"
    downloads_dir: str = "downloads"

    # download
    acknowledge_rights: bool = False


def _build_combined_text(ocr: Dict[str, Any], audio: Optional[Dict[str, Any]]) -> str:
    """Combina transcrição de áudio + texto do OCR em um único blob de texto."""
    ocr_text = (ocr or {}).get("consolidated_text") or ""
    audio_text = (audio or {}).get("text") or ""

    parts = []
    if audio_text.strip():
        parts.append("TRANSCRIÇÃO DO ÁUDIO:\n" + audio_text.strip())
    if ocr_text.strip():
        parts.append("TEXTO NA TELA (OCR):\n" + ocr_text.strip())

    combined = "\n\n".join(parts).strip()
    return combined or "(nenhum texto detectado no áudio nem no OCR)."


def _run_audio_transcription(video_path: str, cfg: PipelineConfig) -> Optional[Dict[str, Any]]:
    """Chama Whisper (se instalado) para transcrever o áudio do vídeo."""
    if not cfg.use_audio:
        return None

    try:
        from reel_analyzer.audio.whisper import WhisperConfig, transcribe_audio
    except ImportError as e:
        log.warning("Whisper não instalado (torch + openai-whisper); pulando áudio: %s", e)
        return None

    wcfg = WhisperConfig(
        model_name=cfg.whisper_model,
        device=cfg.whisper_device,
        language=cfg.whisper_language,
    )

    try:
        log.info("Iniciando transcrição de áudio com Whisper (%s)...", wcfg.model_name)
        audio = transcribe_audio(video_path, wcfg)
        log.info(
            "Transcrição de áudio concluída (len=%d caracteres).",
            len(audio.get("text") or ""),
        )
        return audio
    except Exception as e:
        log.warning("Falha na transcrição de áudio: %s", e)
        return None


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

    # 1) Obter vídeo (download ou arquivo local)
    info: Dict[str, Any] = {}
    if url:
        dl = Downloader(download_dir=cfg.downloads_dir)
        res = dl.download(url, acknowledge_rights=cfg.acknowledge_rights)
        video_path = res.video_path
        info = res.info or {}
    if not video_path:
        raise ValueError("Passe --video (arquivo local) ou --url (com --i-own-this).")

    # 2) Extrair frames
    frames, vmeta = extract_frames(
        video_path,
        every_seconds=cfg.every_seconds,
        max_frames=cfg.frames,
        scene_detect=cfg.scene_detect,
    )
    frames_saved = save_frames(frames, os.path.join(cfg.out_dir, cfg.frames_dir))

    # 3) OCR
    ocr_cfg = OCRConfig(langs=cfg.ocr_langs, tesseract_cmd=cfg.tesseract_cmd)
    frames_as_dict = [
        {"t_sec": fr.t_sec, "image": fr.image, "path": fr.path} for fr in frames_saved
    ]
    ocr = ocr_frames(frames_as_dict, ocr_cfg)

    # 4) Áudio (Whisper)
    audio = _run_audio_transcription(video_path, cfg)

    # 5) Gemini – análise em cima do texto combinado (áudio + OCR)
    ga = GeminiAnalyzer(api_key=gemini_api_key, cfg=GeminiConfig())
    combined_text = _build_combined_text(ocr, audio)
    text_analysis = ga.analyze_text(
        combined_text,
        extra_instructions=extra_instructions,
    )

    # 6) Gemini Vision (opcional)
    vision_analysis = None
    if cfg.vision:
        import pathlib

        image_bytes = []
        for fr in frames_saved[: min(8, len(frames_saved))]:
            if fr.path and os.path.exists(fr.path):
                image_bytes.append(pathlib.Path(fr.path).read_bytes())

        vprompt = (
            "Analise estes frames de um vídeo curto.\n"
            "1) Descreva o que aparece visualmente;\n"
            "2) Extraia texto visível na cena;\n"
            "3) Diga o tema provável e por quê.\n"
            "Responda em PT-BR."
        )
        vision_analysis = ga.analyze_vision(vprompt, image_bytes)

    result: Dict[str, Any] = {
        "input": {"video_path": video_path, "url": url},
        "video_meta": vmeta,
        "download_info": {
            "id": info.get("id"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "upload_date": info.get("upload_date"),
            "webpage_url": info.get("webpage_url"),
        }
        if info
        else {},
        "frames": [
            {"index": fr.index, "t_sec": fr.t_sec, "path": fr.path} for fr in frames_saved
        ],
        "ocr": ocr,
        "audio": audio,
        "gemini": {
            "combined_text": combined_text,
            "text_analysis": text_analysis,
            "vision_analysis": vision_analysis,
        },
    }
    return result


def save_json(result: Dict[str, Any], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
