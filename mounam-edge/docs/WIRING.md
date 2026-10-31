# Wiring: ESP32-S3 N16P8, 2 x INMP441, UDA1334A

Power off before wiring. GPIO numbers below are the **GPIO labels**, not header
pin positions. Check the exact DevKit/breakout silkscreen before applying power.
Use 3.3 V digital signals and a common ground. Keep I2S wiring short, ideally
under 10 cm, with ground returns close to clock/data wires.

## Parts

| Part | Quantity | Role |
| --- | ---: | --- |
| ESP32-S3-WROOM-1 N16P8 DevKit | 1 | 16 MB flash, 8 MB octal PSRAM |
| INMP441 I2S microphone breakout | 2 | Primary and independent reference |
| UDA1334A I2S stereo DAC breakout | 1 | Line-level analog output |
| Stereo line-input headphone amplifier | 1 additional | Common-ground TRS output, volume control, rated for 32-ohm loads |
| Wired earphones | 1 | Connect to headphone amplifier output |
| 100-kohm resistor | 1 | Shared microphone SD pull-down |
| 10-kohm resistor | 1 | DAC MUTE pull-up to 3.3 V during reset |
| 100-nF decoupling capacitor | 2 if absent on breakouts | One across each microphone VDD/GND |
| USB data cable, short jumpers, regulated power | As needed | Bring-up |

**The UDA1334A output is line level and specified for a load of at least 3 kohms.**
A 32-ohm earphone load can produce distortion/current limiting. Use an amplifier
designed for headphones, or a powered speaker/line input. A bridge-output speaker
amplifier must not be wired to common-ground stereo earphones by joining its
negative speaker terminals.

## Digital connections

| ESP32-S3 | Primary INMP441 | Reference INMP441 | UDA1334A |
| --- | --- | --- | --- |
| 3V3 | VDD/VCC | VDD/VCC | Board supply appropriate for its documented 3.3-V operation |
| GND | GND | GND | GND; analog return connected as board documentation specifies |
| GPIO4 | SCK/BCLK | SCK/BCLK | BCLK/BCK |
| GPIO5 | WS/LRCLK | WS/LRCLK | WSEL/WS/LRCLK |
| GPIO6 | SD | SD | No connection |
| GPIO7 | No connection | No connection | DIN/DATA |
| GND | L/R: left slot | No connection | No connection |
| 3V3 | No connection | L/R: right slot | No connection |
| GPIO8 | No connection | No connection | MUTE, active high |
| GPIO10 | No connection | No connection | No connection; oscilloscope timing probe only |

Tie the **two mic SD pins together** and to GPIO6. Fit a 100-kohm pull-down from
this shared wire to GND. INMP441 tri-states SD outside its selected channel;
opposite L/R straps are required. Two microphones strapped to the same channel
must not share SD.

If CHIPEN is exposed, tie it to 3.3 V. Do not leave L/R or CHIPEN floating.
Mic VDD must not receive 5 V. A regulated breakout's VIN is different from a
bare DAC supply pin: only apply the supply voltage its actual board supports.

Connect a 10-kohm resistor from DAC MUTE to **3.3 V**, and connect MUTE to GPIO8.
Firmware holds this pin high during startup, digital mute and audio faults.
The pull-up keeps it asserted while the MCU resets. Verify the breakout really
exposes the UDA1334A's active-high MUTE signal; do not substitute a differently
defined enable pin.

## DAC format and output

Use standard **Philips I2S**, 24 significant bits inside a 32-bit slot. Configure
the DAC for its asynchronous audio/PLL mode, with de-emphasis off. No external
MCLK is generated. For an Adafruit UDA1334A board the default I2S/PLL configuration
already supports this; clones can differ, so check their format/PLL straps.

At 16 kHz, WS is **16 kHz** and BCLK is **1.024 MHz** (64 clocks per stereo frame).
Both DAC channels contain the same enhanced mono stream.

| Analog connection | Destination |
| --- | --- |
| DAC LOUT | Headphone amplifier left line input |
| DAC ROUT | Headphone amplifier right line input |
| DAC analog ground | Amplifier signal ground |
| Amplifier common-ground headphone output | Wired earphones |

Follow the amplifier board's supply, coupling and grounding requirements. Start
with its physical volume at minimum. The firmware's +/-0.25 digital bound is
not a calibrated acoustic sound-pressure limit.

## Microphone placement

Place the primary roughly 3-8 cm from the mouth, with a windscreen. Put the
reference away from the mouth and toward the background source. Start on the
bench with a fan or quiet playback source. Do not put both mics side by side
and expect the algorithm to preserve speech: common speech in the reference
can be cancelled too.

The reference should hear correlated noise before it reaches the primary. The
`delay 0..64` command can delay primary audio by up to 4 ms to accommodate a small
path difference. It adds latency and cannot create a reference for uncorrelated
or unpredictable noise.

## Board checks

Default pins avoid ESP32-S3 N16P8 flash/PSRAM pins and native USB GPIO19/20.
Do not copy classic ESP32 GPIO25/26/27/32 wiring to this module. If changing pins,
check the board schematic for memory, USB, boot straps and onboard peripherals.

The USB-UART connector is used by the supplied control/capture tools. On a board
with separate USB and UART sockets, plug into the **UART** socket. The native
USB socket is not configured as the project's command interface.

Sources: [INMP441 datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf),
[UDA1334ATS datasheet](https://www.nxp.com/docs/en/data-sheet/UDA1334ATS.pdf),
[Adafruit DAC pinout](https://learn.adafruit.com/adafruit-i2s-stereo-decoder-uda1334a/pinouts),
[Espressif I2S guide](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/api-reference/peripherals/i2s.html).
