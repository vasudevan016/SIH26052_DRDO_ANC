#pragma once
#include <cstdint>
// Replaced by ml.train_neural after a source-disjoint public-speech training run.
namespace mounam::neural {
inline constexpr bool kReady = false;
inline constexpr const char* kModelId = "untrained";
inline constexpr const char* kProvenance = "untrained";
inline constexpr unsigned kInputs = 26, kHidden = 24, kOutputs = 8;
inline constexpr float kStrength = 1.0f;
inline constexpr int8_t kW1[24][26] = {};
inline constexpr float kS1[24] = {};
inline constexpr float kB1[24] = {};
inline constexpr int8_t kW2[8][24] = {};
inline constexpr float kS2[8] = {};
inline constexpr float kB2[8] = {};
}
