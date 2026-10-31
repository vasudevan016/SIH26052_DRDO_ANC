# Mounam edge - SIH26052

The new standalone project is in **[mounam-edge](mounam-edge/README.md)**.

It implements the submitted **Edge-Computed Tactical Active Noise Cancellation
(ANC) Node**, Idea 180588, for:

- ESP32-S3-WROOM-1 **N16P8**
- **Two INMP441** I2S microphones
- **UDA1334A** I2S stereo DAC
- Wired earphones through a **stereo headphone amplifier**

| Start here | Link |
| --- | --- |
| Project, architecture and verified limitations | [Project README](mounam-edge/README.md) |
| Pin-by-pin hardware connections | [Wiring](mounam-edge/docs/WIRING.md) |
| Ubuntu terminal build, flash and controls | [Quick start](mounam-edge/docs/QUICKSTART.md) |
| Datasets, real recording and TinyML training | [Training](mounam-edge/docs/TRAINING.md) |
| Test results and hardware measurement plan | [Validation](mounam-edge/docs/VALIDATION.md) |
| Match to submitted presentation | [Idea alignment](mounam-edge/docs/IDEA_ALIGNMENT.md) |

The new audio implementation is entirely offline, with synchronized dual-mic
I2S/DMA, normalized LMS, residual filtering, a tiny speech-presence MLP and real
USB-UART diagnostics. **Firmware builds from `mounam-edge/firmware`; host tools run
from `mounam-edge`.** The older root `src/`, `platformio.ini`, Python dashboard
and web files are an earlier separate prototype and are not the new build entry.

This is a speech enhancement prototype. The bundled ML model is explicitly
synthetic-demo trained; physical latency, real speech scores and ear-level
hearing protection require the separate measurements described in the project.
