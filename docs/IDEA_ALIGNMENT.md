# Alignment with the submitted Mounam idea

Source: the user's SIH26052 statement, Idea ID 180588, and the supplied six-slide
`SIH2026-IDEA-Presentation-Mounam20260929140412.pdf`. Team Mounam, Team ID 186962.
The presentation is not redistributed as a source-code asset.

| Submitted idea or requirement | New project's treatment |
| --- | --- |
| ESP32-S3 edge computation | ESP32-S3-WROOM-1 N16P8 is the sole runtime processor |
| Dual INMP441 digital microphones | Both operate on synchronized I2S slots as primary/reference |
| I2S DMA capture | Actual full-duplex ESP-IDF I2S pipeline, fixed blocks and bounded queues |
| Dedicated Core 1 DSP | Audio task pinned to Core 1; serial work on Core 0 |
| LMS and Wiener mathematical filtering | Bounded normalized LMS plus four-band Wiener-style residual gains |
| AI/ML-enabled problem statement | Tiny learned speech-presence MLP controlling the adaptive/postfilter stages; training/export included |
| UDA1334A output | Actual I2S output, with DAC mute; added headphone amplifier required for 32-ohm earphones |
| Air-gapped/offline operation | No Wi-Fi/Bluetooth initialization, cloud service, MQTT broker or OTA dependency |
| Low latency under 5 ms | Explicit DSP and end-to-end measurement plan; 2-ms blocks alone do not prove this target |
| ESP-DSP/vector math | Portable scalar baseline implemented; acceleration remains a measured optimization |
| Low-cost/low-power production | Candidate architecture; power/BOM are measurements and procurement tasks, not measured results |
| SNR >15 dB, STOI >0.85, PESQ >2.5 | Evaluation tools included; targets remain unverified on real speech/noise |
| Full complex-domain/STFT or large neural enhancer | Not implemented in this MCU baseline; substantial model work needed if required by acceptance |

## Correct technical positioning

The demonstration should be described as an **offline AI-assisted dual-mic speech
enhancement node**. Adaptive noise cancellation in a microphone signal is a valid
signal-processing task. It differs from physical active noise control inside a
headset, which needs an appropriate acoustic error microphone, secondary-path
model, acoustic transducer/enclosure design, calibrated timing and typically
filtered-x adaptive control.

Neither feeding enhanced microphone audio to ordinary earphones nor inverting
an ambient waveform proves cancellation of sound already reaching an ear. The
project does not claim hearing protection, bullet/shock-wave mitigation, military
qualification or authenticated/encrypted radio communication. A real radio
interface and its electrical/protocol requirements are not provided by the
listed hardware.

Offline inference removes network dependence; it does not certify COMSEC,
prevent physical signal interception, or make electronics immune to every form
of electromagnetic interference. No sensitive operational data is needed for
the prototype. Training and capture tools run locally.

The presentation mentions a production BOM under INR 1,000 while the supplied
idea text mentions under INR 2,000. Neither is treated as a verified quote. Include
the headphone amplifier, power regulation, PCB, connectors, housing and assembly
when estimating a complete unit. Likewise, the MCU, DAC, amplifier and regulator
must all be counted in power measurements.

## Path toward the full SIH acceptance goals

1. Establish clean dual-mic recordings and report failures of the adaptive
   baseline, especially uncorrelated noise and reference speech leakage.
2. Train the compact controller on source-disjoint real speech and diverse
   licensed/consented noise; evaluate per class and language.
3. If residual intelligibility remains insufficient, prototype a genuinely
   learned causal sub-band mask/reconstruction model, establish its quality on
   the same holdout, then profile and compress it for the MCU.
4. Profile firmware on the board before changing kernels or DMA depth. Use
   ESP-DSP/ESP-NN optimizations only where their benefit is measured.
5. Complete physical latency, electrical output, power, enclosure and radio
   integration work. Physical headset ANC/hearing protection is a separate
   engineering and validation stage.
