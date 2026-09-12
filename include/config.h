#pragma once

// I2S Microphone Pins (INMP441 ) 
#define I2S_MIC_WS 15
#define I2S_MIC_SD 32
#define I2S_MIC_SCK 14

// I2S Amplifier Pins (MAX98357A)
#define I2S_SPK_BCLK 27
#define I2S_SPK_LRC 26
#define I2S_SPK_DOUT 25

// DSP Configuration
#define SAMPLE_RATE 16000
#define DMA_BUFFER_LEN 512
#define FILTER_TAPS 128
#define LEARNING_RATE 0.01f
