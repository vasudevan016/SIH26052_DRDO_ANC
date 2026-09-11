#include "lms_filter.h"

LMSFilter::LMSFilter(int taps, float learning_rate) {
    num_taps = taps;
    mu = learning_rate;
    weights.assign(num_taps, 0.0f);
    delay_line.assign(num_taps, 0.0f);
}

float LMSFilter::process(float reference_noise, float primary_signal) {
    // Shift delay line backward
    for (int i = num_taps - 1; i > 0; i--) {
        delay_line[i] = delay_line[i - 1];
    }
    delay_line[0] = reference_noise;

    // Calculate filter output (estimated noise signature)
    float estimated_noise = 0.0f;
    for (int i = 0; i < num_taps; i++) {
        estimated_noise += weights[i] * delay_line[i];
    }

    // Calculate error (the isolated clean audio)
    float error_signal = primary_signal - estimated_noise;

    // Update weights for the next sample
    for (int i = 0; i < num_taps; i++) {
        weights[i] += 2.0f * mu * error_signal * delay_line[i];
    }

    return error_signal;
}