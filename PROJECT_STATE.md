# Project state

Last updated: 2026-11-21. Read this first when resuming in a new chat. Update it
after meaningful changes or new camera-test results; keep detailed history in the
changelog and investigation record.

Repository: https://github.com/halk1982/ezviz-dp1c-ha. The previous
`halk1982/ezviz_dp1c_ha` URL redirects to this renamed repository.

## Purpose and stack

Integrate the EZVIZ DP1C door viewer with Home Assistant OS, primarily through the
Cloud Video add-on and Generic Camera. Python 3.12+, `pyezvizapi==1.0.5.0`, FFmpeg/
FFprobe, Python's HTTP server, Docker/Supervisor; pytest and PyAV for development.
An earlier MQTT bridge uses Paho MQTT. Original project code is MIT licensed.

## Completed and current status

- **0.2.4** introduced JPEG snapshots (application commit `782366f`).
- The owner confirmed normal live video with `mode: live`, `decrypt_video: false`,
  `video_mode: compatible`. Unnecessary decryption caused the earlier grey picture.
  Alarm-image encryption does not establish that live video needs decryption.
- `/live.ts` provides authenticated, on-demand video. `/snapshot.jpg` adds fresh
  JPEG captures with a **30-second memory cache**, sharing the same cloud producer
  and credentials. Images are not saved to disk by the snapshot endpoint.
- Startup dependency checks, an HTTP 401 hint, clearer public documentation and
  the MIT license are implemented. Advanced options and the add-on slug are retained.
- The owner reports **0.2.4 is working again**. The earlier log showed successful
  video output, then intermittent EZVIZ stream-start rejections (`5405`, `5404`)
  before media arrived. Those codes' specific meanings remain unverified.
- **Home Assistant still-image delivery is verified on the owner's DP1C**.
  Generic Camera used `/snapshot.jpg`, and the HA camera proxy returned HTTP 200
  with a JPEG while the camera entity was idle. No `5404` or `5405` appeared in
  the reported 2.5-hour HA log window. Apple Home thumbnails and doorbell
  notification images are still pending.
- The log also showed a client disconnect while the add-on sent a snapshot error
  response. A local, unreleased fix suppresses that traceback.
- Keep the existing RenierM26 HACS integration for working motion/alarm images.
  The separate MQTT Cloud Bridge remains an unvalidated prototype.
- The owner confirmed hearing and speaking through their DP1C in the official
  EZVIZ app. Apple Home is the target for intercom. The owner already runs
  Scrypted on HAOS and uses a custom MQTT sensor for doorbell presses.
- **0.2.5** adds opt-in live audio. `live_audio: true` enables AAC when the
  cloud input has a recognized audio track and reports bounded input metadata.
  Physical-camera audio and the DP1C speaker session still need verification.
- Sleep/wake behavior, sustained viewing, battery impact and aarch64 builds
  remain unverified. Keep Preload stream disabled; thumbnail polling can
  repeatedly start live video after the cache expires.

## File map

| File or directory | Responsibility |
|---|---|
| [README.md](README.md) | Public overview, installation and feature status |
| [dp1c_video_probe/config.yaml](dp1c_video_probe/config.yaml) | Add-on version, options, schema and port 8558 |
| [dp1c_video_probe/Dockerfile](dp1c_video_probe/Dockerfile) | Runtime image and startup entry point |
| [dp1c_video_probe/app/bootstrap.py](dp1c_video_probe/app/bootstrap.py) | Startup import and FFmpeg/FFprobe checks |
| [dp1c_video_probe/app/probe.py](dp1c_video_probe/app/probe.py) | Mode selection, authentication/key caches, diagnostic capture |
| [dp1c_video_probe/app/live.py](dp1c_video_probe/app/live.py) | Shared producer lifecycle, HTTP routes and authentication |
| [dp1c_video_probe/app/snapshot.py](dp1c_video_probe/app/snapshot.py) | Bounded JPEG extraction, concurrent captures and short cache |
| [dp1c_video_probe/app/media.py](dp1c_video_probe/app/media.py) / [checks.py](dp1c_video_probe/app/checks.py) | Decryption/remuxing and bounded output diagnostics |
| [dp1c_video_probe/DOCS.md](dp1c_video_probe/DOCS.md) / [CHANGELOG.md](dp1c_video_probe/CHANGELOG.md) | User setup, HomeKit test steps and version history |
| [dp1c/app/](dp1c/app/) / [docs/legacy-bridge.md](docs/legacy-bridge.md) | Earlier MQTT event/alarm-image prototype |
| [tests/](tests/) | Unit tests and synthetic media/HTTP/MQTT smoke checks |
| [docs/investigation.md](docs/investigation.md) | Detailed evidence, prior diagnoses and validation limits |

## Validation and development

At application commit `782366f`: **64 tests passed**. The amd64 container passed
real JPEG decoding/cache/sharing/timeout checks, FFprobe output checks, live HTTP
streaming and encrypted-media regression checks. These used synthetic media and
do not establish physical DP1C or HomeKit compatibility.

With the local client-disconnect fix, **65 tests passed**, along with the JPEG
smoke check. The added regression reproduces the traceback on 0.2.4.

Use the existing checkout and `.venv`; useful commands from the repository root:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python tests/snapshot_smoke.py
```

The smoke check requires FFmpeg/FFprobe. See README for installation and container
checks. Keep credentials, token files, signed URLs and footage out of Git and chat.

With 0.2.5, the local suite passed **71 tests** and all six synthetic media smoke
checks. The amd64 container passed the audio and diagnostic tests, live HTTP,
encrypted media and JPEG extraction from H.264/AAC. The DP1C cloud stream's
audio format remains unverified.

## Immediate next task

Test 0.2.5 on the physical DP1C with `live_audio: true`. Verify the
`LIVE_AUDIO_CHECK` report and listening in Scrypted and Apple Home, using
the setup in [DOCS.md](dp1c_video_probe/DOCS.md#test-listening-in-scrypted-025).
Then verify a DP1C speaker session before wiring Scrypted talkback.

Apple Home still-image validation with 0.2.4 is also pending:

1. Open Apple Home with live viewing closed and verify the doorbell thumbnail.
   Check for a new image after more than 30 seconds and a visible scene change.
2. Press the physical doorbell and verify that the Apple Home notification
   includes an image. Record the result and decide whether to stage another release.
3. Track idle producer shutdown, cold capture latency, sleep/wake and battery use
   separately. If a cloud rejection recurs, allow the 120-second cooldown to finish.
