#include "mounam_dsp.h"
#include "neural_weights.h"
#include <algorithm>
#include <cmath>

namespace mounam {
namespace {
float bound(float x, float lo, float hi) { return std::min(hi, std::max(lo, x)); }
}
std::array<float, kNeuralBands> NeuralBands::tick(float sample) {
    // Causal complementary bands: 125,250,500,1000,2000,3500,5500 Hz edges.
    constexpr float alpha[7] = {0.0479021f,0.0935095f,0.1782750f,0.3247681f,0.5440619f,0.7470098f,0.8846620f};
    std::array<float, kNeuralBands> result{};
    float previous = 0;
    for (size_t i = 0; i < 7; ++i) {
        lowpass[i] += alpha[i]*(sample-lowpass[i]);
        result[i] = lowpass[i]-previous; previous = lowpass[i];
    }
    result[7] = sample-previous;
    return result;
}
void neural_predict(const float* f, float* gains) {
    if (!neural::kReady) {
        for (size_t i = 0; i < kNeuralBands; ++i) gains[i] = 1;
        return;
    }
    float hidden[neural::kHidden];
    for (size_t j = 0; j < neural::kHidden; ++j) {
        float sum = 0;
        for (size_t i = 0; i < kNeuralFeatures; ++i) sum += f[i]*float(neural::kW1[j][i]);
        hidden[j] = std::tanh(neural::kB1[j]+sum*neural::kS1[j]);
    }
    for (size_t j = 0; j < kNeuralBands; ++j) {
        float sum = 0;
        for (size_t i = 0; i < neural::kHidden; ++i) sum += hidden[i]*float(neural::kW2[j][i]);
        const float z = bound(neural::kB2[j]+sum*neural::kS2[j], -30, 30);
        gains[j] = 0.08f+0.92f/(1+std::exp(-z));
    }
}
void NeuralPostfilter::process(const float* residual, const float* reference, const float* clean,
    float probability, float coherence, bool enabled, float* output, float* training_features, float* targets) {
    float buffered[kBlock][kNeuralBands];
    constexpr float smoothing = 0.0031201223f;
    for (size_t i = 0; i < kBlock; ++i) {
        const auto r = residual_bands_.tick(residual[i]);
        const auto n = reference_bands_.tick(reference[i]);
        const auto c = clean_bands_.tick(clean ? clean[i] : 0);
        for (size_t j = 0; j < kNeuralBands; ++j) {
            buffered[i][j] = r[j];
            rp_[j] += smoothing*(r[j]*r[j]-rp_[j]);
            np_[j] += smoothing*(n[j]*n[j]-np_[j]);
            if (clean) cross_[j] += smoothing*(c[j]*r[j]-cross_[j]);
        }
    }
    float f[kNeuralFeatures], predicted[kNeuralBands];
    for (size_t j = 0; j < kNeuralBands; ++j) {
        const float lr = std::log10(std::max(rp_[j], 1e-10f));
        const float ln = std::log10(std::max(np_[j], 1e-10f));
        f[j] = bound((lr+8)/8, 0, 1);
        f[j+8] = bound((ln+8)/8, 0, 1);
        f[j+16] = bound((lr-ln)/2, -1, 1);
        if (targets) targets[j] = bound(cross_[j]/(rp_[j]+1e-10f), 0.08f, 1);
    }
    f[24] = probability; f[25] = coherence;
    if (training_features) std::copy(f, f+kNeuralFeatures, training_features);
    if (enabled) neural_predict(f, predicted);
    else std::fill(predicted, predicted+kNeuralBands, 1.0f);
    for (size_t i = 0; i < kBlock; ++i) {
        float sum = 0;
        for (size_t j = 0; j < kNeuralBands; ++j) {
            const float floor = probability > 0.65f ? 0.35f : 0.08f;
            const float target = 1-neural::kStrength+neural::kStrength*std::max(floor, predicted[j]);
            // Faster opening than closing protects speech onsets and avoids steps.
            const float rate = target > gains_[j] ? 0.02f : 0.004f;
            gains_[j] += rate*(target-gains_[j]);
            sum += gains_[j]*buffered[i][j];
        }
        output[i] = sum;
    }
}
}
