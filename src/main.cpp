#include <Arduino.h>
#include "driver/i2s.h"
#include "config.h"
#include "lms_filter.h"

LMSFilter ancFilter(FILTER_TAPS, LEARNING_RATE);
TaskHandle_t DSPTask;

void configure_i2s() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX), // Master Tx/Rx mode
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = DMA_BUFFER_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = true
    };
    // Install driver config
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL); 
}

// Core 1: DSP Math Execution
void dsp_processing_task(void *pvParameters) {
    int32_t mic_buffer[DMA_BUFFER_LEN * 2]; // L/R Interleaved audio
    int32_t spk_buffer[DMA_BUFFER_LEN * 2];
    size_t bytes_read, bytes_written;

    while (1) {
        // Read raw I2S DMA buffers sent from Core 0
        i2s_read(I2S_NUM_0, &mic_buffer, sizeof(mic_buffer), &bytes_read, portMAX_DELAY);

        // Process audio block
        for (int i = 0; i < DMA_BUFFER_LEN * 2; i += 2) {
            // Normalize 32-bit integer scale to float for DSP math
            float reference_noise = (float)mic_buffer[i] / 2147483648.0f; // Left Mic
            float primary_signal = (float)mic_buffer[i+1] / 2147483648.0f; // Right Mic

            // Execute C++ LMS Adaptive Filter
            float clean_audio = ancFilter.process(reference_noise, primary_signal);

            // Denormalize float back to 32-bit I2S frame
            spk_buffer[i] = (int32_t)(clean_audio * 2147483648.0f);
            spk_buffer[i+1] = spk_buffer[i];
        }

        // Write processed output to amplifier via DMA
        i2s_write(I2S_NUM_0, &spk_buffer, bytes_read, &bytes_written, portMAX_DELAY);
    }
}

void setup() {
    Serial.begin(115200);
    configure_i2s();

    // Pin high-speed C++ logic to Core 1 
    xTaskCreatePinnedToCore(dsp_processing_task, "DSP_Task", 10000, NULL, 1, &DSPTask, 1);
}

void loop() {
    // Delete standard loop to dedicate Core 0 purely to RTOS background tasks
    vTaskDelete(NULL); 
}