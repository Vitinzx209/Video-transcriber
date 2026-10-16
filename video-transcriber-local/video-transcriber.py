"""Transcritor local de vídeo: servidor HTTP em 127.0.0.1 que extrai o áudio com FFmpeg
e transcreve com faster-whisper. Nada sai do seu computador."""
import base64, glob, json, math, os, shutil, subprocess, tempfile, wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from faster_whisper import WhisperModel

HOST = "127.0.0.1"
PORT = int(os.environ.get("TRANSCRIBER_PORT", "8765"))
MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")      # tiny, base, small, medium, large-v3
LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "pt")        # "pt", "en"... ou vazio para detectar
HERE = os.path.dirname(os.path.abspath(__file__))


def find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found: return found
    patterns = [
        os.path.join(HERE, "ffmpeg*", "**", "ffmpeg.exe"),
        os.path.join(os.path.expanduser("~"), "Downloads", "ffmpeg*", "**", "ffmpeg.exe"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path): return path
    return None


FFMPEG = find_ffmpeg()
print(f"FFmpeg: {FFMPEG or 'NÃO ENCONTRADO'}", flush=True)
print(f"Carregando modelo Whisper '{MODEL_NAME}'; no primeiro uso pode demorar...", flush=True)
MODEL = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
print(f"Transcritor pronto em http://{HOST}:{PORT}", flush=True)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health": self.send_error(404); return
        self.reply({"ok": True, "status": "ready"})
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-expected-duration")
        # Chrome may send this preflight header when a website talks to loopback.
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
    def do_POST(self):
        if self.path != "/transcribe": self.send_error(404); return
        try:
            ctype = (self.headers.get("content-type") or "").split(";")[0].strip().lower()
            size = int(self.headers.get("content-length", "0"))
            if not FFMPEG:
                raise FileNotFoundError("Não encontrei o FFmpeg. Instale-o (winget install Gyan.FFmpeg) ou coloque a pasta ffmpeg* ao lado deste script.")
            with tempfile.TemporaryDirectory() as d:
                video, audio = os.path.join(d, "video.mp4"), os.path.join(d, "audio.wav")
                if ctype == "application/json":
                    # Formato antigo (base64 em JSON); só serve para vídeos pequenos.
                    body = json.loads(self.rfile.read(size))
                    raw = base64.b64decode(body.get("video_base64", ""))
                    if not raw: raise ValueError("video_base64 vazio")
                    expected = float(body.get("expected_duration") or 0)
                    with open(video, "wb") as f: f.write(raw)
                else:
                    # Formato novo: o vídeo chega como arquivo binário e é gravado em disco aos poucos.
                    expected = float(self.headers.get("x-expected-duration") or 0)
                    remaining = size
                    with open(video, "wb") as f:
                        while remaining > 0:
                            chunk = self.rfile.read(min(1 << 20, remaining))
                            if not chunk: break
                            f.write(chunk)
                            remaining -= len(chunk)
                    if remaining > 0: raise ValueError(f"Envio do vídeo incompleto: faltaram {remaining} bytes.")
                    if size == 0: raise ValueError("O vídeo chegou vazio.")
                if not math.isfinite(expected) or expected < 0:
                    raise ValueError("Duração esperada inválida")
                print(f"Vídeo recebido: {os.path.getsize(video) / 1048576:.1f} MB. Extraindo áudio...", flush=True)
                subprocess.run([FFMPEG, "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", audio], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with wave.open(audio, "rb") as wav:
                    duration = wav.getnframes() / wav.getframerate()
                print(f"Áudio recebido: {duration:.1f}s; player: {expected:.1f}s", flush=True)
                if expected and abs(duration - expected) > max(2, expected * 0.01):
                    raise ValueError(f"Duração diferente: recebi {duration:.1f}s de áudio, mas o player informa {expected:.1f}s. O vídeo inteiro não foi confirmado; nenhuma análise completa foi registrada.")
                segments, _ = MODEL.transcribe(audio, language=LANGUAGE or None, vad_filter=True)
                entries = []
                for segment in segments:
                    if segment.text.strip():
                        entries.append({"start": segment.start, "end": segment.end, "text": segment.text.strip()})
                        print(f"Fala transcrita até {segment.end:.1f}s / {duration:.1f}s", flush=True)
                text = " ".join(s["text"] for s in entries)
                if not text:
                    raise ValueError("Nenhuma fala foi reconhecida no áudio recebido.")
                print(f"Processamento finalizado: {duration:.1f}s de áudio; {len(entries)} trechos de fala.", flush=True)
            self.reply({"ok": True, "text": text, "segments": entries, "audio_duration": duration, "duration_verified": bool(expected)})
        except Exception as e: self.reply({"ok": False, "error": str(e)}, 500)
    def reply(self, data, status=200):
        out=json.dumps(data, ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Content-Length",str(len(out))); self.end_headers(); self.wfile.write(out)

ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
