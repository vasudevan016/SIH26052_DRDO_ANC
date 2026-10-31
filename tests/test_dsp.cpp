#include "mounam_dsp.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <random>

using namespace mounam;
int main() {
    assert(unpack_i2s(0x000000ff) == 0);
    assert(unpack_i2s(std::numeric_limits<int32_t>::min()) == -1.0f);
    assert(std::fabs(unpack_i2s(0x40000000) - 0.5f) < 1e-7f);
    for (float value : {-1.0f, -0.6f, 0.0f, 0.6f, 1.0f})
        assert(std::fabs(unpack_i2s(pack_i2s(value))-value) < 3e-7f);
    assert(pack_i2s(std::numeric_limits<float>::quiet_NaN()) == 0);
    assert(crc32("123456789", 9) == 0xcbf43926u);
    DcBlock dc;
    float last = 0;
    for (unsigned i = 0; i < 16000; ++i) last = dc.tick(0.3f);
    assert(std::fabs(last) < 1e-10f);
    Bands bands;
    for (unsigned i = 0; i < 1000; ++i) {
        float sample = 0.2f*std::sin(float(i)*0.17f);
        auto b = bands.tick(sample);
        assert(std::fabs(b[0]+b[1]+b[2]+b[3]-sample) < 1e-6f);
    }
    Engine engine;
    float p[kBlock], r[kBlock], out[kBlock];
    for (size_t i = 0; i < kBlock; ++i) p[i] = r[i] = 0.1f;
    engine.process(p, r, out);
    for (float y : out) assert(y == 0); // Startup must be silent.
    Settings settings;
    settings.muted = false; settings.output_gain = 1; settings.mode = Mode::Dsp;
    engine.configure(settings); engine.reset();
    assert(!engine.settings().muted && engine.settings().output_gain == 1);
    std::mt19937 random(26052);
    std::uniform_real_distribution<float> noise(-0.06f, 0.06f);
    float hist[16]{};
    unsigned head = 0;
    double before = 0, after = 0;
    for (unsigned block = 0; block < 1500; ++block) {
        for (size_t i = 0; i < kBlock; ++i) {
            hist[head] = r[i] = noise(random);
            p[i] = 0.65f*hist[(head+16-3)%16] + 0.2f*hist[(head+16-9)%16];
            head = (head+1)%16;
        }
        engine.process(p, r, out);
        if (block > 1000) for (size_t i = 0; i < kBlock; ++i) { before += p[i]*p[i]; after += out[i]*out[i]; }
    }
    const double improvement = 10*std::log10(before/(after+1e-15));
    std::printf("Correlated synthetic noise reduction after convergence: %.2f dB\n", improvement);
    assert(improvement > 15); // Algorithm test, NOT a speech/defence performance result.
    assert(engine.metrics().max_weight <= 2.0f);
    // Long stability run with clipping, impulses, silent reference, NaN and infinity.
    for (unsigned block = 0; block < 5000; ++block) {
        for (size_t i = 0; i < kBlock; ++i) { p[i] = noise(random)*20; r[i] = block%4 ? noise(random) : 0; }
        if (block%31 == 0) p[3] = std::numeric_limits<float>::infinity();
        if (block%29 == 0) r[5] = std::numeric_limits<float>::quiet_NaN();
        engine.process(p, r, out);
        for (float y : out) assert(std::isfinite(y) && std::fabs(y) <= 0.25f);
    }
    settings.muted = true;
    engine.configure(settings); engine.process(p, r, out);
    for (float y : out) assert(y == 0); // Immediate mute after previously running.
    // Reference timing compensation and limits stay bounded at the maximum delay.
    settings.primary_delay = 1000; settings.output_gain = std::numeric_limits<float>::quiet_NaN();
    engine.configure(settings);
    assert(engine.settings().primary_delay == 64 && engine.settings().output_gain == 0);
    std::puts("DSP invariants passed.");
}
