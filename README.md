# SIH26052 Edge-ANC System

```text
SIH26052_DRDO_ANC/
├── src/
│   ├── main.cpp         # FreeRTOS dual-core tasks and I2S configuration
│   ├── lms_filter.cpp   # C++ implementation of the Adaptive Filter
│   └── lms_filter.h
├── include/
│   └── config.h         # I2S Pin definitions and DSP hyperparameters
├── platformio.ini       # Hardware configuration for ESP32-S3
└── README.md
