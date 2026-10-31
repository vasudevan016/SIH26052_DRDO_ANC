#include "mounam_dsp.h"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <random>

int main() {
    mounam::Engine engine;
    mounam::Settings settings;
    settings.muted = false;
    engine.configure(settings);
    float p[mounam::kBlock], r[mounam::kBlock], out[mounam::kBlock];
    std::mt19937 rng(26052);
    std::uniform_real_distribution<float> noise(-0.05f, 0.05f);
    for (size_t i = 0; i < mounam::kBlock; ++i) {
        r[i] = noise(rng); p[i] = 0.8f*r[i]+0.006f*std::sin(float(i));
    }
    constexpr unsigned blocks = 50000;
    for (unsigned i = 0; i < 1000; ++i) engine.process(p, r, out);
    const auto start = std::chrono::steady_clock::now();
    for (unsigned i = 0; i < blocks; ++i) engine.process(p, r, out);
    const double ns = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now()-start).count();
    std::printf("{\"scope\":\"host_only_not_ESP32_latency\",\"blocks\":%u,\"mean_block_us\":%.4f,\"checksum\":%.8f}\n",
        blocks, ns/blocks/1000, double(out[0]));
}
