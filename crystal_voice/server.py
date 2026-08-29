"""Dependency-free local validation server; deliberately offline, not WebRTC."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit

from crystal_voice import __version__
from crystal_voice.adapters.base import Extraction, TargetSpeakerExtractor
from crystal_voice.audio import apply_headroom, decode_wav, encode_wav, fingerprint, peak_dbfs, clipped_samples
from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.selftest import run_startup_self_test
from crystal_voice.adapters.restoration import SpExPlusMossFormerSRAdapter


class Session:
    def __init__(self, adapter: TargetSpeakerExtractor):
        self.adapter = adapter
        self.profile = None
        self.profile_sha256 = None
        self.files = Path(tempfile.mkdtemp(prefix="crystal-voice-ui-"))


def handler_factory(session: Session):
    static = Path(__file__).with_name("static")

    class Handler(BaseHTTPRequestHandler):
        server_version = f"CrystalVoice/{__version__}"

        def _json(self, status: int, payload: dict):
            body = json.dumps(payload, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> bytes:
            size = int(self.headers.get("Content-Length", 0))
            if size <= 0 or size > 50_000_000:
                raise ValueError("Upload must be between 1 byte and 50 MB")
            return self.rfile.read(size)

        def do_GET(self):
            # Browsers may add cache-busting query strings such as
            # /app.js?v=manual-stop-2 and /audio/raw.wav?12345. Route using the
            # URL path only so versioned static assets and playback always work.
            request_path = urlsplit(self.path).path
            if request_path == "/":
                body = (static / "index.html").read_bytes()
                content_type = "text/html; charset=utf-8"
            elif request_path == "/app.js":
                body = (static / "app.js").read_bytes()
                content_type = "text/javascript; charset=utf-8"
            elif request_path == "/api/status":
                return self._json(200, {"ready": True, "version": __version__, "model": session.adapter.name, "model_version": session.adapter.version, "profile_ready": session.profile is not None})
            elif request_path in {"/audio/raw.wav", "/audio/isolation.wav", "/audio/processed.wav"}:
                path = session.files / request_path.rsplit("/", 1)[1]
                if not path.exists():
                    return self.send_error(404)
                body, content_type = path.read_bytes(), "audio/wav"
            else:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            try:
                request_path = urlsplit(self.path).path
                body = self._body()
                audio = decode_wav(body)
                if request_path == "/api/enroll":
                    session.profile = session.adapter.enroll(audio)
                    session.profile_sha256 = fingerprint(body)
                    return self._json(200, {"profile_ready": True, "duration_seconds": audio.duration, "sha256": session.profile_sha256})
                if request_path == "/api/process":
                    if session.profile is None:
                        raise ValueError("Record a 3–5 second Target Voice Profile first")
                    capture_id = fingerprint(body)
                    # Persist raw before decoding/extraction: playback is the exact uploaded take.
                    (session.files / "raw.wav").write_bytes(body)
                    started = time.perf_counter()
                    if isinstance(session.adapter, SpExPlusMossFormerSRAdapter):
                        isolation = session.adapter.extractor.extract(audio, session.profile)
                        isolated_safe, isolation_attenuation = apply_headroom(isolation.audio)
                        (session.files / "isolation.wav").write_bytes(encode_wav(isolated_safe))
                        result = session.adapter.restore(Extraction(isolated_safe, isolation.metadata))
                    else:
                        result = session.adapter.extract(audio, session.profile)
                        isolated_safe, isolation_attenuation = apply_headroom(result.audio)
                        (session.files / "isolation.wav").write_bytes(encode_wav(isolated_safe))
                    safe, attenuation = apply_headroom(result.audio)
                    processed = encode_wav(safe)
                    (session.files / "processed.wav").write_bytes(processed)
                    elapsed = time.perf_counter() - started
                    return self._json(200, {
                        "capture_id": capture_id,
                        "raw_source_sha256": capture_id,
                        "isolation_source_sha256": capture_id,
                        "processed_source_sha256": capture_id,
                        "same_take_verified": True,
                        "raw_peak_dbfs": peak_dbfs(audio),
                        "processed_peak_dbfs": peak_dbfs(safe),
                        "isolation_peak_dbfs": peak_dbfs(isolated_safe),
                        "clipped_samples": clipped_samples(safe),
                        "attenuation_db": attenuation,
                        "isolation_attenuation_db": isolation_attenuation,
                        "processing_seconds": elapsed,
                        "real_time_factor": elapsed / audio.duration,
                        "model": session.adapter.name,
                        "conditioned_by_reference": result.metadata.get("conditioned_by_reference", False),
                    })
                return self.send_error(404)
            except Exception as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})

        def log_message(self, format, *args):
            print(f"[ui] {self.address_string()} {format % args}")

    return Handler


def serve(adapter: TargetSpeakerExtractor, host: str = "127.0.0.1", port: int = 8765) -> None:
    adapter.load()  # Fail visibly before reporting the server as ready.
    if isinstance(adapter, ClearerVoiceSpExPlusAdapter):
        run_startup_self_test(adapter)
    elif isinstance(adapter, SpExPlusMossFormerSRAdapter):
        run_startup_self_test(adapter)
    server = ThreadingHTTPServer((host, port), handler_factory(Session(adapter)))
    print(f"Crystal Voice {__version__} ready with {adapter.name} at http://{host}:{port}")
    server.serve_forever()
