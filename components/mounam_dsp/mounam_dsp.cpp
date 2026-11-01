#include "mounam_dsp.h"
#include "model_weights.h"
#include "neural_weights.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace mounam {
namespace {
float clamp(float x, float lo, float hi) { return std::min(hi, std::max(lo, x)); }
float finite_audio(float x) { return std::isfinite(x) ? clamp(x, -1.0f, 1.0f) : 0.0f; }
float safe_log(float x) { return std::log10(std::max(x, 1e-10f)); }
}
float DcBlock::tick(float sample) {
    const float result = sample - x + 0.995f * y;
    x = sample; y = result;
    return result;
}
std::array<float, 4> Bands::tick(float sample) {
    // 1-exp(-2*pi*fc/16000), fc = 300, 1200, 3000 Hz.
    l0 += 0.111134f * (sample - l0);
    l1 += 0.375772f * (sample - l1);
    l2 += 0.692136f * (sample - l2);
    return {l0, l1 - l0, l2 - l1, sample - l2};
}
void Features::process(const float* primary, const float* reference,
                       float* hp_primary, float* hp_reference, float* f) {
    constexpr float a = 0.0031201223f; // 20 ms EWMA at 16 kHz
    for (size_t i = 0; i < kBlock; ++i) {
        const float p = dp_.tick(finite_audio(primary[i]));
        const float r = dr_.tick(finite_audio(reference[i]));
        hp_primary[i] = p; hp_reference[i] = r;
        pp_ += a * (p*p - pp_); rr_ += a * (r*r - rr_);
        cross_ += a * (p*r - cross_);
        zcr_ += a * (float((p >= 0) != (previous_ >= 0)) - zcr_);
        previous_ = p;
        const auto b = bands_.tick(p);
        for (size_t j = 0; j < 4; ++j) bp_[j] += a * (b[j]*b[j] - bp_[j]);
    }
    const float sum = bp_[0] + bp_[1] + bp_[2] + bp_[3] + 1e-10f;
    f[0] = clamp((safe_log(pp_) + 8.0f) / 8.0f, 0, 1);
    f[1] = clamp((safe_log(rr_) + 8.0f) / 8.0f, 0, 1);
    f[2] = clamp((safe_log(pp_ + 1e-10f) - safe_log(rr_ + 1e-10f)) / 2, -1, 1);
    f[3] = clamp(zcr_, 0, 1);
    f[4] = bp_[0] / sum; f[5] = (bp_[1] + bp_[2]) / sum; f[6] = bp_[3] / sum;
    f[7] = clamp(std::fabs(cross_) / std::sqrt(pp_*rr_ + 1e-20f), 0, 1);
}
float speech_probability(const float* f) {
    if (!model::kTrained) {
        // Explicit DSP fallback, not described as machine learning.
        return (f[2] > 0.15f && f[5] > 0.15f) ? 0.9f : 0.1f;
    }
    float z = model::kB2;
    for (size_t j = 0; j < model::kHidden; ++j) {
        float h = model::kB1[j];
        for (size_t i = 0; i < kFeatures; ++i) h += f[i] * model::kW1[j][i];
        z += std::tanh(h) * model::kW2[j];
    }
    return 1.0f / (1.0f + std::exp(-clamp(z, -30, 30)));
}
float unpack_i2s(int32_t word) {
    // INMP441: signed 24-bit MSB-aligned inside a 32-bit slot. Ignore floating LSBs.
    const uint32_t masked = static_cast<uint32_t>(word) & 0xffffff00u;
    int32_t signed_word;
    std::memcpy(&signed_word, &masked, sizeof(signed_word));
    return static_cast<float>(signed_word) / 2147483648.0f;
}
int32_t pack_i2s(float sample) {
    // Multiplication, not left-shifting a negative signed value (undefined in C++).
    const auto pcm24 = static_cast<int32_t>(std::lrintf(finite_audio(sample) * 8388607.0f));
    return pcm24 * 256;
}
int16_t pack_pcm16(float sample) {
    return static_cast<int16_t>(std::lrintf(finite_audio(sample) * 32767.0f));
}
uint32_t crc32(const void* data, size_t bytes) {
    auto p = static_cast<const uint8_t*>(data);
    uint32_t crc = 0xffffffffu;
    while (bytes--) {
        crc ^= *p++;
        for (unsigned i = 0; i < 8; ++i) crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}
void Engine::reset() {
    const Settings s = settings_;
    *this = Engine{};
    settings_ = s;
}
void Engine::configure(const Settings& s) {
    settings_ = s;
    settings_.output_gain = std::isfinite(s.output_gain) ? clamp(s.output_gain, 0, 1) : 0;
    settings_.primary_delay = std::min(s.primary_delay, 64u);
    if (static_cast<unsigned>(s.mode) > 3) settings_.mode = Mode::Hybrid;
}
void Engine::process(const float* primary, const float* reference, float* output,
    const float* clean, float* training_features, float* targets) {
    float hp[kBlock], hr[kBlock], f[kFeatures];
    features_.process(primary, reference, hp, hr, f);
    const float probability = settings_.noise_only ? 0 : (settings_.mode == Mode::Hybrid ? speech_probability(f)
        : ((f[2] > 0.15f && f[5] > 0.15f) ? 0.9f : 0.1f));
    metrics_.speech_probability = probability;
    float power = 0, ref_power = 0, peak = 0;
    for (size_t i = 0; i < kBlock; ++i) {
        power += hp[i]*hp[i]; ref_power += hr[i]*hr[i];
        peak = std::max(peak, std::fabs(hp[i]));
        if (std::fabs(primary[i]) >= 0.98f || std::fabs(reference[i]) >= 0.98f) ++metrics_.input_clipped;
    }
    power /= kBlock; ref_power /= kBlock;
    const bool impulse = peak > 0.12f && peak > 7.0f * std::sqrt(previous_power_ + 1e-8f);
    previous_power_ += 0.08f * (power - previous_power_);
    if (impulse) { impulse_gain_ = 0.15f; ++metrics_.impulse_blocks; }
    const bool speech_guard = !settings_.noise_only && f[2] > 0.3f && f[5] > 0.18f;
    const float adapt = (settings_.hold || impulse || speech_guard) ? 0.0f
        : 0.12f * (1.0f - 0.98f * probability);
    float out_power = 0;
    std::array<float, 4> current_band_power{};
    float residual[kBlock], classical[kBlock], clean_hp[kBlock], neural_output[kBlock];
    for (size_t i = 0; i < kBlock; ++i) {
        primary_delay_[delay_head_] = hp[i];
        const size_t read = (delay_head_ + primary_delay_.size() - settings_.primary_delay) % primary_delay_.size();
        const float p = primary_delay_[read];
        delay_head_ = (delay_head_ + 1) % primary_delay_.size();
        head_ = (head_ + kTaps - 1) % kTaps;
        history_[head_] = hr[i];
        float estimate = 0, norm = 1e-6f;
        for (size_t j = 0; j < kTaps; ++j) {
            const float x = history_[(head_ + j) % kTaps];
            estimate += weights_[j] * x; norm += x*x;
        }
        const float error = p - estimate;
        residual[i] = error;
        if (clean) clean_hp[i] = clean_dc_.tick(finite_audio(clean[i]));
        if (adapt > 0 && ref_power > 1e-8f) {
            const float step = adapt * clamp(error, -1, 1) / norm;
            for (size_t j = 0; j < kTaps; ++j) {
                const float x = history_[(head_ + j) % kTaps];
                weights_[j] = clamp(0.999999f * weights_[j] + step*x, -2, 2);
            }
        }
        const auto bands = post_bands_.tick(error);
        float enhanced = 0;
        for (size_t j = 0; j < 4; ++j) {
            current_band_power[j] += bands[j]*bands[j] / kBlock;
            enhanced += band_gain_[j] * bands[j];
        }
        classical[i] = enhanced;
    }
    neural_post_.process(residual, hr, clean ? clean_hp : nullptr, probability, f[7],
        settings_.mode == Mode::Hybrid, neural_output, training_features, targets);
    metrics_.band_gains = neural_post_.gains();
    for (size_t i = 0; i < kBlock; ++i) {
        const float enhanced = settings_.mode == Mode::Hybrid && neural::kReady ? neural_output[i] : classical[i];
        float chosen = enhanced * impulse_gain_;
        if (settings_.mode == Mode::Primary) chosen = hp[i];
        if (settings_.mode == Mode::Reference) chosen = hr[i];
        impulse_gain_ += 0.002f * (1.0f - impulse_gain_);
        // Immediate mute, gradual unmute. A digital bound cannot establish safe SPL.
        if (settings_.muted) ramp_ = 0;
        else ramp_ = std::min(1.0f, ramp_ + 1.0f / 320.0f);
        float y = chosen * settings_.output_gain * ramp_;
        if (!std::isfinite(y)) y = 0;
        if (std::fabs(y) > 0.25f) ++metrics_.output_limited;
        y = clamp(y, -0.25f, 0.25f);
        output[i] = y; out_power += y*y / kBlock;
    }
    for (size_t j = 0; j < 4; ++j) {
        band_power_[j] += 0.15f * (current_band_power[j] - band_power_[j]);
        if (probability < 0.35f && !impulse) noise_power_[j] += 0.03f * (band_power_[j] - noise_power_[j]);
        const float floor = probability > 0.55f ? 0.60f : 0.20f;
        const float wiener = std::sqrt(std::max(0.0f, 1 - noise_power_[j] / (band_power_[j] + 1e-10f)));
        const float desired = std::max(floor, wiener);
        band_gain_[j] += 0.15f * (desired - band_gain_[j]);
    }
    metrics_.primary_rms = std::sqrt(power);
    metrics_.reference_rms = std::sqrt(ref_power);
    metrics_.output_rms = std::sqrt(out_power);
    metrics_.max_weight = 0;
    for (float w : weights_) metrics_.max_weight = std::max(metrics_.max_weight, std::fabs(w));
}
}
