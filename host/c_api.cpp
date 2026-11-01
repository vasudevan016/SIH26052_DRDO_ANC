#include "mounam_dsp.h"
#include "model_weights.h"
#include "neural_weights.h"
#include <new>

extern "C" {
void* mounam_create() { return new (std::nothrow) mounam::Engine; }
void mounam_destroy(void* p) { delete static_cast<mounam::Engine*>(p); }
void mounam_configure(void* p, unsigned mode, unsigned muted, float gain, unsigned hold, unsigned delay) {
    if (!p) return;
    mounam::Settings s;
    s.mode = static_cast<mounam::Mode>(mode); s.muted = muted != 0;
    s.output_gain = gain; s.hold = hold != 0; s.primary_delay = delay;
    static_cast<mounam::Engine*>(p)->configure(s);
}
void mounam_process(void* p, const float* stereo, float* out, size_t frames) {
    auto engine = static_cast<mounam::Engine*>(p);
    for (size_t n = 0; n + mounam::kBlock <= frames; n += mounam::kBlock) {
        float primary[mounam::kBlock], reference[mounam::kBlock];
        for (size_t i = 0; i < mounam::kBlock; ++i) {
            primary[i] = stereo[2*(n+i)]; reference[i] = stereo[2*(n+i)+1];
        }
        engine->process(primary, reference, out+n);
    }
}
void* mounam_features_create() { return new (std::nothrow) mounam::Features; }
void mounam_features_destroy(void* p) { delete static_cast<mounam::Features*>(p); }
void mounam_extract(void* p, const float* stereo, float* out, size_t frames) {
    auto features = static_cast<mounam::Features*>(p);
    for (size_t n = 0; n + mounam::kBlock <= frames; n += mounam::kBlock) {
        float primary[mounam::kBlock], reference[mounam::kBlock], hp[mounam::kBlock], hr[mounam::kBlock];
        for (size_t i = 0; i < mounam::kBlock; ++i) {
            primary[i] = stereo[2*(n+i)]; reference[i] = stereo[2*(n+i)+1];
        }
        features->process(primary, reference, hp, hr, out+(n/mounam::kBlock)*mounam::kFeatures);
    }
}
float mounam_predict(const float* features) { return mounam::speech_probability(features); }
const char* mounam_model_provenance() { return mounam::model::kProvenance; }
const char* mounam_model_id() { return mounam::model::kModelId; }
const char* mounam_neural_id() { return mounam::neural::kModelId; }
const char* mounam_neural_provenance() { return mounam::neural::kProvenance; }
void mounam_neural_predict(const float* features, float* gains) { mounam::neural_predict(features, gains); }
void mounam_training(void* p, const float* stereo, const float* clean, float* features, float* targets, size_t frames) {
    auto engine = static_cast<mounam::Engine*>(p);
    for (size_t n = 0; n + mounam::kBlock <= frames; n += mounam::kBlock) {
        float primary[mounam::kBlock], reference[mounam::kBlock], out[mounam::kBlock];
        for (size_t i = 0; i < mounam::kBlock; ++i) {
            primary[i] = stereo[2*(n+i)]; reference[i] = stereo[2*(n+i)+1];
        }
        engine->process(primary, reference, out, clean+n,
            features+(n/mounam::kBlock)*mounam::kNeuralFeatures, targets+(n/mounam::kBlock)*mounam::kNeuralBands);
    }
}
}
