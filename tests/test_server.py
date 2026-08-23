from http.client import HTTPConnection
from threading import Thread

from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.audio import encode_wav
from crystal_voice.fixtures import synthetic_case
from crystal_voice.server import Session, ThreadingHTTPServer, handler_factory


def test_one_uploaded_take_is_raw_and_processed_source():
    adapter = SameTakeDiagnosticAdapter(); adapter.load()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(Session(adapter)))
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    reference, mixture, _ = synthetic_case("speech_0db")
    # Fixture reference is 4 seconds and therefore a valid profile.
    connection = HTTPConnection("127.0.0.1", server.server_port)
    connection.request("POST", "/api/enroll", encode_wav(reference), {"Content-Type": "audio/wav"})
    assert connection.getresponse().status == 200
    raw = encode_wav(mixture)
    connection.request("POST", "/api/process", raw, {"Content-Type": "audio/wav"})
    response = connection.getresponse()
    payload = __import__("json").loads(response.read())
    assert response.status == 200
    assert payload["same_take_verified"] is True
    assert payload["raw_source_sha256"] == payload["isolation_source_sha256"] == payload["processed_source_sha256"]
    connection.request("GET", "/audio/isolation.wav")
    assert connection.getresponse().status == 200
    server.shutdown(); server.server_close()
