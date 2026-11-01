#pragma once
#include <array>
#include <cstdint>
#include <cstddef>
#include <algorithm>

namespace mounam {
// Fixed storage. Percentiles are histogram-bin upper bounds, not acoustic delay.
struct TimingStats {
    std::array<uint32_t,128> bins{};
    uint32_t count = 0, maximum = 0;
    uint64_t total_us = 0;
    void observe(uint32_t us) {
        ++bins[std::min(us/16,127u)]; ++count; total_us += us;
        maximum = std::max(maximum, us);
    }
    uint32_t percentile_upper(unsigned percent) const {
        if (!count) return 0;
        const uint64_t target = (uint64_t(count)*std::min(percent,100u)+99)/100;
        uint64_t seen = 0;
        for (size_t i = 0; i < bins.size(); ++i) {
            seen += bins[i];
            if (seen >= target) return i == bins.size()-1 ? maximum : uint32_t((i+1)*16);
        }
        return maximum;
    }
};
}
