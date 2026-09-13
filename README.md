# 🛡️ DRDO Edge-ANC Virtual Node [SIH26052]

An AI/ML-enabled Active Noise Cancellation (ANC) telemetry dashboard and edge-compute architecture designed for high-noise tactical environments (armored vehicles, rotary-wing aircraft, artillery zones). 

**Target Hardware:** ESP32-S3 (Core 1 pinned for DSP)
**Latency Target:** < 5ms (Sub-perceptual)
**Algorithmic Approach:** TinyML-driven Spectral Masking & LMS Adaptive Filtering

## 📡 System Architecture
This repository contains the Command & Control (C2) Python telemetry interface and the embedded C++ DSP logic.
1. **Input:** I2S MEMS Microphone captures raw acoustic data (Speech + Combat Noise).
2. **Edge Processing:** ESP32-S3 bypasses standard CPU overhead using Direct Memory Access (DMA). A Recurrent Neural Network (RNN) extracts Mel-frequency cepstral coefficients (MFCCs) to classify and suppress non-speech frames.
3. **Output:** Phase-inverted anti-noise is generated via I2S DAC to the tactical headset.
4. **Telemetry:** Python dashboard visualizes real-time Time-Domain waveforms, FFT Spectrum Analysis, and SNR attenuation metrics.

## ⚙️ C2 Dashboard Features
* **Real-Time Oscilloscope:** Visualizes the raw vs. ML-cleaned audio waveforms.
* **FFT Spectrogram:** Proves 0-4kHz human vocal preservation while low-frequency rumble bands collapse.
* **Dynamic Noise Profiles:** Simulates Tank, Helicopter, and Artillery acoustic environments.
* **Live SNR Telemetry:** Calculates Root Mean Square (RMS) variance for accurate dB reduction reporting.

## 🛠️ Bill of Materials (BOM)
Designed for mass deployment and strict cost efficiency:
* **Compute:** ESP32-S3 WROOM-1 (~₹450)
* **Input:** INMP441 I2S Omnidirectional Microphone (~₹150)
* **Output:** MAX98357A I2S Amplifier (~₹120)
* **Total Cost:** < ₹1,000 per node
