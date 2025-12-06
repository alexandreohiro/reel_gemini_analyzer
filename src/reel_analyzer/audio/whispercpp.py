import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class WhisperConfig:
    model_name: str = "small"
    device: str = "cpu"            # "cuda" se tiver GPU
    language: Optional[str] = "pt"  # None = auto
    translate: bool = False        # True = traduz para inglês


_model_cache: Dict[str, Any] = {}


def _load_model(cfg: WhisperConfig):
    """Carrega e faz cache do modelo Whisper."""
    key = f"{cfg.model_name}-{cfg.device}"
    if key in _model_cache:
        return _model_cache[key]

    import whisper  # openai-whisper

    log.info("Carregando modelo Whisper '%s' (%s)...", cfg.model_name, cfg.device)
    model = whisper.load_model(cfg.model_name, device=cfg.device)
    _model_cache[key] = model
    return model


def transcribe_audio(video_path: str, cfg: WhisperConfig) -> Dict[str, Any]:
    """
    Transcreve o áudio do vídeo usando openai-whisper.

    Requer:
        pip install torch openai-whisper
        ffmpeg instalado e no PATH.
    """
    model = _load_model(cfg)

    options: Dict[str, Any] = {}
    if cfg.language is not None:
        options["language"] = cfg.language
    options["task"] = "translate" if cfg.translate else "transcribe"

    log.info("Transcrevendo áudio de %s ...", video_path)
    result = model.transcribe(video_path, **options)

    text = (result.get("text") or "").strip()
    segments_out = []
    for s in result.get("segments") or []:
        segments_out.append(
            {
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "text": s.get("text", "").strip(),
            }
        )

    return {
        "text": text,
        "language": result.get("language"),
        "duration": float(result.get("duration", 0.0)),
        "segments": segments_out,
        "model": cfg.model_name,
        "device": cfg.device,
    }
