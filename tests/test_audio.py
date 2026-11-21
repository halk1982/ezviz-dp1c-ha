"""Exercise the live producer with locally generated MPEG-PS."""
from contextlib import AbstractContextManager
import io
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from live import produce


pytestmark = pytest.mark.skipif(
    not all(shutil.which(binary) for binary in ("ffmpeg", "ffprobe")),
    reason="Live audio tests require FFmpeg and FFprobe",
)


@pytest.mark.parametrize(("video_mode", "source_audio", "live_audio", "video_delay"), [
    ("copy", True, True, 0),
    ("compatible", True, True, 0),
    ("compatible", True, True, 1.2),
    ("compatible", False, True, 0),
    ("compatible", True, False, 0),
    ("compatible", True, None, 0),
])
def test_live_audio_output_and_input_diagnostic(tmp_path, capsys, video_mode, source_audio, live_audio, video_delay):
    fixture = ["ffmpeg", "-v", "error"]
    if video_delay:
        fixture += ["-itsoffset", str(video_delay)]
    fixture += ["-f", "lavfi", "-i", "testsrc2=s=320x240:r=10"]
    if source_audio:
        fixture += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000", "-c:a", "mp2", "-ac", "2"]
    fixture += ["-t", "5" if video_delay else "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-fps_mode", "passthrough", "-bf", "0", "-f", "mpeg", "pipe:1"]
    source = subprocess.run(fixture, check=True, capture_output=True, timeout=10).stdout
    packets = [SimpleNamespace(encrypted=False, body=source[offset:offset + 997])
               for offset in range(0, len(source), 997)]
    class Stream(AbstractContextManager):
        def __exit__(self, *_):
            self.close()

        def close(self):
            pass

        def start(self):
            return SimpleNamespace(result=0)

        def iter_packets(self, *, max_packets=None):
            yield from packets

    client = SimpleNamespace(last_codes={}, export_token=lambda: {})
    options = tmp_path / "options.json"
    settings = {"account": "synthetic", "password": "PRIVATE_PASSWORD", "serial": "PRIVATE_SERIAL",
                "video_mode": video_mode}
    if live_audio is not None:
        settings["live_audio"] = live_audio
    options.write_text(json.dumps(settings))
    auth = tmp_path / "live_auth.json"
    auth.write_text(json.dumps({"identity": "synthetic", "token": {}}))

    output = io.BytesIO()
    assert produce(options, auth, output=output, open_stream=lambda *a, **k: Stream(),
                   client_factory=lambda *a, **k: client) == 0

    media = output.getvalue()
    tracks = subprocess.run([
        "ffprobe", "-v", "error", "-f", "mpegts", "-show_streams",
        "-show_entries", "stream=codec_type,codec_name,start_time,channels", "-of", "json", "pipe:0",
    ], input=media, check=True, capture_output=True, timeout=10)
    streams = {track["codec_type"]: track for track in json.loads(tracks.stdout)["streams"]}
    codecs = {kind: track["codec_name"] for kind, track in streams.items()}
    expected_codecs = {"video": "h264", "audio": "aac"} if source_audio and live_audio else {"video": "h264"}
    assert codecs == expected_codecs
    if source_audio and live_audio:
        assert streams["audio"]["channels"] == 1
    if video_delay:
        offset = float(streams["video"]["start_time"]) - float(streams["audio"]["start_time"])
        assert offset == pytest.approx(video_delay, abs=0.15)
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", "pipe:0", "-f", "null", "-"],
                   input=media, check=True, capture_output=True, timeout=10)

    logs = capsys.readouterr().err
    summaries = [json.loads(line.partition(": ")[2]) for line in logs.splitlines()
                 if line.startswith("LIVE_AUDIO_CHECK: ")]
    if live_audio and source_audio:
        assert summaries == [{"status": "detected", "codec": "mp2", "sample_rate": 16000, "channels": 2}]
    elif live_audio:
        assert summaries == [{"status": "not_detected"}]
    else:
        assert summaries == []
    assert "PRIVATE" not in logs
