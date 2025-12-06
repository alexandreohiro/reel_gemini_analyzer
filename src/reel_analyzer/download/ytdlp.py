import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import yt_dlp

log = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    video_path: str
    info: dict

class Downloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download(self, url: str, *, acknowledge_rights: bool = False) -> DownloadResult:
        host = urlparse(url).netloc.lower()
        if ("instagram.com" in host or "www.instagram.com" in host) and not acknowledge_rights:
            raise PermissionError(
                "Para URLs do Instagram, use --i-own-this (apenas conteúdo seu ou com permissão). "
                "Ou baixe o arquivo e use --video."
            )

        outtmpl = os.path.join(self.download_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        log.info("Baixando via yt-dlp...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # força mp4 quando possível (yt-dlp também pode fazer merge)
        if not filename.endswith(".mp4") and os.path.exists(filename):
            base, _ = os.path.splitext(filename)
            mp4 = base + ".mp4"
            try:
                os.replace(filename, mp4)
                filename = mp4
            except Exception:
                pass

        log.info("Download concluído: %s", filename)
        return DownloadResult(video_path=filename, info=info or {})
