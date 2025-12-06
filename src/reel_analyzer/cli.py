import argparse
import os
import sys
from datetime import datetime

from reel_analyzer.utils.logging_config import setup_logging
from reel_analyzer.pipeline import PipelineConfig, run_pipeline, save_json

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reel-analyze", description="Video -> frames -> OCR -> Gemini analysis")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--video", help="Caminho para o arquivo de vídeo local (mp4)")
    g.add_argument("--url", help="URL do vídeo (use apenas se você tem permissão)")

    p.add_argument("--out", default=None, help="Caminho do JSON de saída (default: results/analysis_<timestamp>.json)")
    p.add_argument("--out-dir", default="results", help="Diretório base de saída (default: results)")

    p.add_argument("--frames", type=int, default=12, help="Quantidade máxima de frames (default: 12)")
    p.add_argument("--every-seconds", type=float, default=None, help="Extrair 1 frame a cada X segundos")
    p.add_argument("--scene-detect", action="store_true", help="Tentar pegar frames por mudança de cena (simples)")

    p.add_argument("--vision", action="store_true", help="Enviar alguns frames para o Gemini (além do OCR)")
    p.add_argument("--ocr-langs", default="por+eng", help="Idiomas do Tesseract (default: por+eng)")
    p.add_argument("--tesseract-cmd", default=None, help="Path do tesseract.exe (Windows)")

    p.add_argument("--gemini-api-key", default=None, help="API key (ou use env GEMINI_API_KEY)")
    p.add_argument("--extra", default=None, help="Instruções extras para o Gemini (string)")

    p.add_argument("--i-own-this", action="store_true", help="Reconheço que tenho direito/permissão para baixar via URL.")
    p.add_argument("--log-level", default="INFO", help="INFO, DEBUG, WARNING...")

    return p

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)

    if args.gemini_api_key is None:
        args.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    cfg = PipelineConfig(
        frames=args.frames,
        every_seconds=args.every_seconds,
        scene_detect=args.scene_detect,
        vision=args.vision,
        ocr_langs=args.ocr_langs,
        tesseract_cmd=args.tesseract_cmd,
        out_dir=args.out_dir,
        acknowledge_rights=bool(args.i_own_this),
    )

    out = args.out
    if not out:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(args.out_dir, f"analysis_{ts}.json")

    result = run_pipeline(
        video_path=args.video,
        url=args.url,
        gemini_api_key=args.gemini_api_key,
        extra_instructions=args.extra,
        cfg=cfg,
    )
    save_json(result, out)
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
