#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace mounam {
inline constexpr size_t kBlock = 32;
inline constexpr size_t kFeatures = 8;
inline constexpr size_t kTaps = 64;
inline constexpr unsigned kSampleRate = 16000;

enum class Mode : unsigned { Primary = 0, Reference = 1, Dsp = 2, Hybrid = 3 };
struct Settings {
    Mode mode = Mode::Hybrid;
    bool muted = true;
    bool hold = false;
    float output_gain = 0.05f;
    unsigned primary_delay = 0; // 0..64 samples; adds delay, never predicts noise
};
struct Metrics {
    float primary_rms = 0, reference_rms = 0, output_rms = 0;
    float speech_probability = 0, max_weight = 0;
    uint32_t input_clipped = 0, output_limited = 0, impulse_blocks = 0;
};
struct DcBlock {
    float x = 0, y = 0;
    float tick(float sample);
};
struct Bands {
    float l0 = 0, l1 = 0, l2 = 0;
    std::array<float, 4> tick(float sample);
};

// Causal 20-ms exponentially smoothed features. No FFT/lookahead allocation.
class Features {
public:
    void process(const float* primary, const float* reference,
                 float* hp_primary, float* hp_reference, float* features);
private:
    DcBlock dp_, dr_;
    Bands bands_;
    float pp_ = 0, rr_ = 0, cross_ = 0, zcr_ = 0, previous_ = 0;
    std::array<float, 4> bp_{};
};

float speech_probability(const float* features);
float unpack_i2s(int32_t word);
int32_t pack_i2s(float sample);
int16_t pack_pcm16(float sample);
uint32_t crc32(const void* data, size_t bytes);

// Own one instance on the audio task. All state is fixed-size; no heap in process.
class Engine {
public:
    void reset();
    void configure(const Settings& settings);
    const Settings& settings() const { return settings_; }
    const Metrics& metrics() const { return metrics_; }
    void process(const float* primary, const float* reference, float* output);
private:
    Settings settings_{};
    Metrics metrics_{};
    Features features_;
    Bands post_bands_;
    std::array<float, kTaps> weights_{}, history_{};
    std::array<float, 65> primary_delay_{};
    std::array<float, 4> noise_power_{{1e-8f, 1e-8f, 1e-8f, 1e-8f}};
    std::array<float, 4> band_power_{}, band_gain_{{1, 1, 1, 1}};
    size_t head_ = 0, delay_head_ = 0;
    float previous_power_ = 1e-5f, impulse_gain_ = 1, ramp_ = 0;
};
}
