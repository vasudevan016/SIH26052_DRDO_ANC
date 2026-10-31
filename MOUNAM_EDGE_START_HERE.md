# Mounam edge: new standalone SIH26052 project

The new implementation is in [mounam-edge/README.md](mounam-edge/README.md).

It targets the **ESP32-S3-WROOM-1 N16P8**, **two INMP441 microphones** and a
**UDA1334A DAC**, with offline adaptive filtering, a tiny trainable speech-presence
model, real serial telemetry, microphone capture and paired evaluation tools.

Start with [the wiring guide](mounam-edge/docs/WIRING.md), then
[the Ubuntu terminal setup](mounam-edge/docs/QUICKSTART.md).

The older files in the repository root are a separate earlier prototype. Build
the new firmware from `mounam-edge/firmware`, and run host commands from
`mounam-edge`. The new project has its own configuration and requirements.
