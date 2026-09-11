#pragma once
#include <vector>

class LMSFilter {
private:
    int num_taps;
    float mu; // Learning rate
    std::vector<float> weights;
    std::vector<float> delay_line;

public:
    LMSFilter(int taps, float learning_rate);
    float process(float reference_noise, float primary_signal);
};