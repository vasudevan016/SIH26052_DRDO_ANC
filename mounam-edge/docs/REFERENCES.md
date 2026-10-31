# Primary technical references

These references were checked while designing the project. Hardware specifics
must be checked against the exact breakout and DevKit revision in use.

| Reference | Used for |
| --- | --- |
| [Espressif ESP-IDF v5.4.3 I2S](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/api-reference/peripherals/i2s.html) | Full duplex, standard Philips mode, DMA, callbacks, preload and auto-clear |
| [Espressif ESP-IDF v5.4.3 UART](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/api-reference/peripherals/uart.html) | Serial driver and bounded control/capture task |
| [Espressif Linux toolchain setup](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/get-started/linux-macos-setup.html) | Terminal installation and SDK setup |
| [TDK/InvenSense INMP441 datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf) | 24-bit I2S, 64 clocks/frame, shared SD with opposite slots, pull-down and startup |
| [NXP UDA1334ATS datasheet](https://www.nxp.com/docs/en/data-sheet/UDA1334ATS.pdf) | 16-kHz operation, PLL mode, I2S format, active-high mute and analog load |
| [Adafruit UDA1334A pinout](https://learn.adafruit.com/adafruit-i2s-stereo-decoder-uda1334a/pinouts) | Breakout line output and headphone amplifier requirement |

The user's uploaded Mounam presentation and SIH26052 statement define the
project's objective and chosen hardware. They are design inputs; their latency,
protection, cost and performance assertions are not substituted for measurements.
