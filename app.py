"""
Descargador multimedia local (YouTube, TikTok, Instagram, X/Twitter).
Backend Flask + yt-dlp. Solo para uso personal/local.
"""
import os
import re
import uuid
import threading
import shutil
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file, abort
import yt_dlp

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Detección / validación de plataforma
# ---------------------------------------------------------------------------
PLATFORM_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)", re.I),
    "tiktok": re.compile(r"tiktok\.com", re.I),
    "instagram": re.compile(r"instagram\.com", re.I),
    "x": re.compile(r"(twitter\.com|x\.com)", re.I),
}

URL_RE = re.compile(r"^https?://[^\s]+$", re.I)


def detect_platform(url: str) -> str | None:
    for name, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return name
    return None


# ---------------------------------------------------------------------------
# Resoluciones y formatos soportados
# ---------------------------------------------------------------------------
# Nota: "144p" es la resolución estándar más baja disponible en la mayoría de
# plataformas (el pedido original mencionaba "140p", que no es una resolución
# de video real -- itag 140 en YouTube es en realidad un audio; se usa 144p).
RESOLUTIONS = {
    "144p": 144,
    "240p": 240,
    "360p": 360,
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
    "1440p (2K)": 1440,
    "2160p (4K)": 2160,
}

AUDIO_FORMATS = {"mp3", "wav", "aac"}

# ---------------------------------------------------------------------------
# Estado de trabajos en memoria (suficiente para uso local de un solo usuario)
# ---------------------------------------------------------------------------
jobs_lock = threading.Lock()
jobs = {}  # job_id -> dict(status, percent, error, filename, filepath)


def set_job(job_id, **kwargs):
    with jobs_lock:
        jobs[job_id].update(kwargs)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def make_progress_hook(job_id):
    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            percent = round(downloaded / total * 100, 1) if total else None
            set_job(
                job_id,
                status="downloading",
                percent=percent,
                speed=d.get("_speed_str", "").strip(),
                eta=d.get("eta"),
            )
        elif d.get("status") == "finished":
            set_job(job_id, status="processing", percent=100)

    return hook


def run_download(job_id, url, mode, quality):
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(job_dir / "%(title).150s.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [make_progress_hook(job_id)],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if mode == "audio":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": quality,  # mp3 | wav | aac
                "preferredquality": "192",
            }
        ]
    else:
        height = RESOLUTIONS.get(quality)
        if height is None:
            set_job(job_id, status="error", error=f"Resolución no soportada: {quality}")
            return
        ydl_opts["format"] = (
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best[height<={height}]"
        )
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        set_job(job_id, status="error", error=_clean_error(str(e)))
        return
    except Exception as e:  # noqa: BLE001
        set_job(job_id, status="error", error=str(e))
        return

    produced = list(job_dir.glob("*"))
    if not produced:
        set_job(job_id, status="error", error="No se generó ningún archivo de salida.")
        return

    result_file = produced[0]
    set_job(
        job_id,
        status="done",
        percent=100,
        filename=result_file.name,
        filepath=str(result_file),
    )


def _clean_error(msg: str) -> str:
    msg = msg.replace("ERROR: ", "").strip()
    if "Unsupported URL" in msg:
        return "La URL no es compatible con ninguna plataforma soportada."
    if "Video unavailable" in msg or "This video is unavailable" in msg:
        return "El video no está disponible (puede ser privado, eliminado o restringido por región)."
    if "Private video" in msg:
        return "Este contenido es privado y no se puede descargar."
    if "HTTP Error 404" in msg:
        return "No se encontró el contenido en la URL indicada."
    return msg[:300]


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        resolutions=list(RESOLUTIONS.keys()),
        audio_formats=sorted(AUDIO_FORMATS),
        ffmpeg_ok=ffmpeg_available(),
    )


@app.route("/api/detect", methods=["POST"])
def api_detect():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not URL_RE.match(url):
        return jsonify({"ok": False, "error": "URL inválida. Debe comenzar con http:// o https://"}), 400
    platform = detect_platform(url)
    if not platform:
        return jsonify({"ok": False, "error": "Plataforma no soportada. Usa YouTube, TikTok, Instagram o X."}), 400
    return jsonify({"ok": True, "platform": platform})


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    mode = data.get("mode")  # "video" | "audio"
    quality = data.get("quality")  # resolución o formato de audio

    if not URL_RE.match(url):
        return jsonify({"ok": False, "error": "URL inválida."}), 400

    platform = detect_platform(url)
    if not platform:
        return jsonify({"ok": False, "error": "Plataforma no soportada. Usa YouTube, TikTok, Instagram o X."}), 400

    if mode not in ("video", "audio"):
        return jsonify({"ok": False, "error": "Modo inválido, debe ser 'video' o 'audio'."}), 400

    if mode == "audio" and quality not in AUDIO_FORMATS:
        return jsonify({"ok": False, "error": "Formato de audio no soportado."}), 400

    if mode == "video" and quality not in RESOLUTIONS:
        return jsonify({"ok": False, "error": "Resolución no soportada."}), 400

    if not ffmpeg_available():
        return jsonify({
            "ok": False,
            "error": "ffmpeg no está instalado o no está en el PATH. Es requerido para combinar video/audio "
                     "y convertir formatos de audio. Revisa el README para instalarlo.",
        }), 500

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "percent": 0, "platform": platform, "mode": mode, "quality": quality}

    thread = threading.Thread(target=run_download, args=(job_id, url, mode, quality), daemon=True)
    thread.start()

    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/progress/<job_id>")
def api_progress(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Trabajo no encontrado."}), 404
    safe_job = {k: v for k, v in job.items() if k != "filepath"}
    return jsonify({"ok": True, **safe_job})


@app.route("/api/file/<job_id>")
def api_file(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        abort(404)
    filepath = job.get("filepath")
    if not filepath or not os.path.exists(filepath):
        abort(404)
    return send_file(filepath, as_attachment=True, download_name=job.get("filename"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
