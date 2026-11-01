#include "mounam_dsp.h"
#include "model_weights.h"
#include "neural_weights.h"
#include "timing_stats.h"
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "driver/uart.h"
#include "esp_err.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#if ESP_IDF_VERSION < ESP_IDF_VERSION_VAL(5, 4, 0)
#error "Use ESP-IDF v5.4.3 (the tested/pinned toolchain)."
#endif
static_assert(CONFIG_IDF_TARGET_ESP32S3, "This firmware targets ESP32-S3, not classic ESP32.");
static_assert(CONFIG_MOUNAM_BCLK != CONFIG_MOUNAM_WS && CONFIG_MOUNAM_BCLK != CONFIG_MOUNAM_DIN
    && CONFIG_MOUNAM_BCLK != CONFIG_MOUNAM_DOUT && CONFIG_MOUNAM_WS != CONFIG_MOUNAM_DIN
    && CONFIG_MOUNAM_WS != CONFIG_MOUNAM_DOUT && CONFIG_MOUNAM_DIN != CONFIG_MOUNAM_DOUT,
    "I2S data and clock GPIOs must be distinct.");
static_assert(CONFIG_MOUNAM_PROBE != CONFIG_MOUNAM_BCLK && CONFIG_MOUNAM_PROBE != CONFIG_MOUNAM_WS
    && CONFIG_MOUNAM_PROBE != CONFIG_MOUNAM_DIN && CONFIG_MOUNAM_PROBE != CONFIG_MOUNAM_DOUT,
    "Probe GPIO must be distinct from audio GPIOs.");
static_assert(CONFIG_MOUNAM_MUTE != CONFIG_MOUNAM_BCLK && CONFIG_MOUNAM_MUTE != CONFIG_MOUNAM_WS
    && CONFIG_MOUNAM_MUTE != CONFIG_MOUNAM_DIN && CONFIG_MOUNAM_MUTE != CONFIG_MOUNAM_DOUT
    && CONFIG_MOUNAM_MUTE != CONFIG_MOUNAM_PROBE, "DAC mute GPIO must be distinct.");

namespace {
using namespace mounam;
constexpr uart_port_t kUart = UART_NUM_0;
i2s_chan_handle_t tx_channel, rx_channel;
QueueHandle_t command_queue, snapshot_queue, capture_queue;
// ESP-IDF disables hardware atomics on this target. Keep these critical sections
// to a single load/store; never use a potentially locking C++ atomic in the ISR.
portMUX_TYPE state_mux = portMUX_INITIALIZER_UNLOCKED;
uint32_t rx_overflows = 0;
bool capturing = false;
uint32_t overflow_count() {
    portENTER_CRITICAL(&state_mux);
    const uint32_t result = rx_overflows;
    portEXIT_CRITICAL(&state_mux);
    return result;
}
bool capture_active() {
    portENTER_CRITICAL(&state_mux);
    const bool result = capturing;
    portEXIT_CRITICAL(&state_mux);
    return result;
}
void set_capture(bool value) {
    portENTER_CRITICAL(&state_mux);
    capturing = value;
    portEXIT_CRITICAL(&state_mux);
}

enum class Operation { Mode, Mute, Gain, Hold, Delay, Reset, Demo, Calibrate };
struct Command { Operation operation; float value; };
struct Snapshot {
    Settings settings;
    Metrics metrics;
    uint32_t blocks = 0, max_dsp_us = 0, late_blocks = 0, io_errors = 0, capture_drops = 0;
    float dsp_ewma_us = 0;
    uint32_t calibration_blocks = 0;
    TimingStats timing;
    bool fault = false;
};
// Little endian on ESP32-S3. CRC-32 covers the 128-byte PCM payload.
struct __attribute__((packed)) CapturePacket {
    char magic[4] = {'M', 'A', 'N', 'C'};
    uint8_t version = 1, channels = 2;
    uint16_t frames = kBlock;
    uint32_t sequence = 0, drops = 0, crc = 0;
    int16_t pcm[2*kBlock]{};
};
static_assert(sizeof(CapturePacket) == 148);

void send_text(const char* format, ...) {
    char line[2048];
    va_list args;
    va_start(args, format);
    const int n = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (n > 0) uart_write_bytes(kUart, line, size_t(n) < sizeof(line) ? size_t(n) : sizeof(line)-1);
}
bool on_rx_overflow(i2s_chan_handle_t, i2s_event_data_t*, void*) {
    portENTER_CRITICAL_ISR(&state_mux);
    ++rx_overflows;
    portEXIT_CRITICAL_ISR(&state_mux);
    return false;
}
void initialize_audio() {
    ESP_ERROR_CHECK(gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_MUTE), 1));
    ESP_ERROR_CHECK(gpio_set_direction(static_cast<gpio_num_t>(CONFIG_MOUNAM_MUTE), GPIO_MODE_OUTPUT));
    ESP_ERROR_CHECK(gpio_set_direction(GPIO_NUM_0, GPIO_MODE_INPUT));
    ESP_ERROR_CHECK(gpio_set_pull_mode(GPIO_NUM_0, GPIO_PULLUP_ONLY));
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    channel.dma_desc_num = 3;
    channel.dma_frame_num = kBlock;
    channel.auto_clear = true; // TX starvation produces zeros, rather than replaying stale audio.
    ESP_ERROR_CHECK(i2s_new_channel(&channel, &tx_channel, &rx_channel));
    i2s_std_config_t standard{};
    standard.clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(kSampleRate);
    standard.slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_STEREO);
    standard.gpio_cfg.mclk = I2S_GPIO_UNUSED;
    standard.gpio_cfg.bclk = static_cast<gpio_num_t>(CONFIG_MOUNAM_BCLK);
    standard.gpio_cfg.ws = static_cast<gpio_num_t>(CONFIG_MOUNAM_WS);
    standard.gpio_cfg.din = static_cast<gpio_num_t>(CONFIG_MOUNAM_DIN);
    standard.gpio_cfg.dout = static_cast<gpio_num_t>(CONFIG_MOUNAM_DOUT);
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(tx_channel, &standard));
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_channel, &standard));
    i2s_event_callbacks_t callbacks{};
    callbacks.on_recv_q_ovf = on_rx_overflow;
    ESP_ERROR_CHECK(i2s_channel_register_event_callback(rx_channel, &callbacks, nullptr));
    int32_t silence[2*kBlock*3]{};
    size_t loaded = 0;
    ESP_ERROR_CHECK(i2s_channel_preload_data(tx_channel, silence, sizeof(silence), &loaded));
    ESP_ERROR_CHECK(i2s_channel_enable(tx_channel));
    ESP_ERROR_CHECK(i2s_channel_enable(rx_channel));
    ESP_ERROR_CHECK(gpio_set_direction(static_cast<gpio_num_t>(CONFIG_MOUNAM_PROBE), GPIO_MODE_OUTPUT));
}
void audio_task(void*) {
    static Engine engine; // BSS/internal RAM. No allocation, UART, filesystem or radio in audio loop.
    static int32_t rx[2*kBlock], tx[2*kBlock];
    float primary[kBlock], reference[kBlock], output[kBlock];
    Snapshot s;
    unsigned warmup = 200; // 400 ms: INMP441 needs 2^18 BCLK cycles at startup (~256 ms here).
    uint32_t previous_overflows = 0;
    for (;;) {
        Command c;
        while (xQueueReceive(command_queue, &c, 0) == pdTRUE) {
            Settings settings = engine.settings();
            if (c.operation != Operation::Calibrate && s.calibration_blocks) {
                s.calibration_blocks = 0; settings.noise_only = false;
            }
            switch (c.operation) {
                case Operation::Mode: settings.mode = static_cast<Mode>(unsigned(c.value)); break;
                case Operation::Mute: settings.muted = c.value != 0; break;
                case Operation::Gain: settings.output_gain = c.value; break;
                case Operation::Hold: settings.hold = c.value != 0; break;
                case Operation::Delay: settings.primary_delay = unsigned(c.value); engine.reset(); break;
                case Operation::Reset: settings.muted = true; engine.reset(); warmup = 200; break;
                case Operation::Demo:
                    settings = Settings{}; settings.muted = false;
                    break; // Keep learned acoustic-path coefficients after calibration.
                case Operation::Calibrate:
                    engine.reset(); settings.noise_only = true;
                    settings.muted = true; settings.hold = false;
                    s.calibration_blocks = 1500; break; // 3 s, without blocking either core.
            }
            engine.configure(settings);
        }
        size_t bytes = 0;
        const esp_err_t read_result = i2s_channel_read(rx_channel, rx, sizeof(rx), &bytes, 20);
        const uint32_t overflows = overflow_count();
        if (read_result != ESP_OK || bytes != sizeof(rx) || overflows != previous_overflows) {
            ++s.io_errors; s.fault = true;
        }
        previous_overflows = overflows;
        if (s.fault) {
            // Flush queued output and stop both clocks. Recovery requires reboot, not stale buffers.
            gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_MUTE), 1);
            std::memset(tx, 0, sizeof(tx));
            i2s_channel_disable(tx_channel);
            i2s_channel_disable(rx_channel);
            s.settings = engine.settings(); s.settings.muted = true;
            xQueueOverwrite(snapshot_queue, &s);
            vTaskDelete(nullptr);
            return;
        }
        for (size_t i = 0; i < kBlock; ++i) {
            primary[i] = unpack_i2s(rx[2*i]); reference[i] = unpack_i2s(rx[2*i+1]);
        }
        const int64_t start = esp_timer_get_time();
        gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_PROBE), 1);
        engine.process(primary, reference, output);
        gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_PROBE), 0);
        const uint32_t elapsed = uint32_t(esp_timer_get_time() - start);
        s.timing.observe(elapsed);
        if (elapsed > s.max_dsp_us) s.max_dsp_us = elapsed;
        s.dsp_ewma_us += 0.01f * (float(elapsed)-s.dsp_ewma_us);
        if (elapsed >= 1000000*kBlock/kSampleRate) ++s.late_blocks;
        if (warmup) { --warmup; std::memset(output, 0, sizeof(output)); }
        gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_MUTE), engine.settings().muted || warmup ? 1 : 0);
        for (size_t i = 0; i < kBlock; ++i) tx[2*i] = tx[2*i+1] = pack_i2s(output[i]);
        bytes = 0;
        const esp_err_t write_result = i2s_channel_write(tx_channel, tx, sizeof(tx), &bytes, 20);
        if (write_result != ESP_OK || bytes != sizeof(tx)) {
            ++s.io_errors; s.fault = true;
            gpio_set_level(static_cast<gpio_num_t>(CONFIG_MOUNAM_MUTE), 1);
        }
        if (capture_active() && !warmup) {
            CapturePacket packet;
            packet.sequence = s.blocks; packet.drops = s.capture_drops;
            for (size_t i = 0; i < kBlock; ++i) {
                packet.pcm[2*i] = pack_pcm16(primary[i]); packet.pcm[2*i+1] = pack_pcm16(reference[i]);
            }
            packet.crc = crc32(reinterpret_cast<const uint8_t*>(&packet)+20, sizeof(packet)-20);
            if (xQueueSend(capture_queue, &packet, 0) != pdTRUE) ++s.capture_drops;
        }
        ++s.blocks;
        s.settings = engine.settings(); s.metrics = engine.metrics();
        if (s.calibration_blocks && --s.calibration_blocks == 0) {
            Settings done = engine.settings(); done.noise_only = false; done.muted = true;
            engine.configure(done); s.settings = done;
        }
        // Report silence truthfully during startup.
        if (warmup) s.metrics.output_rms = 0;
        // Control needs 10-Hz snapshots, not 500 cross-core copies per second.
        if (s.blocks == 1 || s.blocks % 50 == 0) xQueueOverwrite(snapshot_queue, &s);
    }
}
void print_stats(const Snapshot& s) {
    send_text("{\"type\":\"stats\",\"status\":\"%s\",\"sample_rate\":16000,\"block_frames\":32,\"psram_bytes\":%lu,"
        "\"model\":\"%s\",\"model_id\":\"%s\",\"mode\":%u,\"muted\":%s,\"gain\":%.4f,\"hold\":%s,\"primary_delay\":%u,"
        "\"primary_rms\":%.7f,\"reference_rms\":%.7f,\"output_rms\":%.7f,\"speech_probability\":%.4f,"
        "\"blocks\":%lu,\"max_dsp_us\":%lu,\"dsp_ewma_us\":%.2f,\"late_blocks\":%lu,\"rx_overflows\":%lu,"
        "\"io_errors\":%lu,\"input_clipped\":%lu,\"output_limited\":%lu,\"impulse_blocks\":%lu,"
        "\"capture_drops\":%lu,\"calibrating\":%s,\"neural_model\":\"%s\",\"neural_id\":\"%s\","
        "\"dsp_p50_upper_us\":%lu,\"dsp_p95_upper_us\":%lu,\"dsp_p99_upper_us\":%lu,"
        "\"band_gains\":[%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f]}\n",
        s.fault ? "fault_reboot_required" : "streaming", (unsigned long)esp_psram_get_size(), model::kProvenance, model::kModelId,
        unsigned(s.settings.mode), s.settings.muted ? "true" : "false", double(s.settings.output_gain),
        s.settings.hold ? "true" : "false", s.settings.primary_delay,
        double(s.metrics.primary_rms), double(s.metrics.reference_rms), double(s.metrics.output_rms),
        double(s.metrics.speech_probability), (unsigned long)s.blocks, (unsigned long)s.max_dsp_us,
        double(s.dsp_ewma_us), (unsigned long)s.late_blocks, (unsigned long)overflow_count(), (unsigned long)s.io_errors,
        (unsigned long)s.metrics.input_clipped, (unsigned long)s.metrics.output_limited,
        (unsigned long)s.metrics.impulse_blocks, (unsigned long)s.capture_drops,
        s.calibration_blocks ? "true" : "false", neural::kProvenance, neural::kModelId,
        (unsigned long)s.timing.percentile_upper(50), (unsigned long)s.timing.percentile_upper(95),
        (unsigned long)s.timing.percentile_upper(99),
        double(s.metrics.band_gains[0]), double(s.metrics.band_gains[1]), double(s.metrics.band_gains[2]),
        double(s.metrics.band_gains[3]), double(s.metrics.band_gains[4]), double(s.metrics.band_gains[5]),
        double(s.metrics.band_gains[6]), double(s.metrics.band_gains[7]));
}
bool parse_number(const char* text, float low, float high, float& result) {
    char* end = nullptr;
    result = strtof(text, &end);
    return end != text && *end == '\0' && std::isfinite(result) && result >= low && result <= high;
}
void handle_line(const char* line, const Snapshot& s) {
    if (!std::strcmp(line, "capture on")) {
        if (s.fault) { send_text("{\"error\":\"audio fault; reboot board\"}\n"); return; }
        xQueueReset(capture_queue); set_capture(true); return;
    }
    if (!std::strcmp(line, "capture off")) {
        set_capture(false); xQueueReset(capture_queue);
        send_text("{\"capture\":false}\n"); return;
    }
    if (capture_active()) return; // In binary mode only capture off is a valid control command.
    if (!std::strcmp(line, "stats")) { print_stats(s); return; }
    if (!std::strcmp(line, "help")) {
        send_text("Commands: demo; calibrate (stay quiet 3s, output muted); stats; mode hybrid|dsp|primary|reference; mute on|off; gain 0..1; "
            "hold on|off; delay 0..64; reset; capture on|off\n"); return;
    }
    if (s.fault) { send_text("{\"error\":\"audio fault; press RESET to reboot\"}\n"); return; }
    Command command{};
    float value;
    bool valid = true;
    if (!std::strcmp(line, "demo")) command = {Operation::Demo, 0};
    else if (!std::strcmp(line, "calibrate")) command = {Operation::Calibrate, 0};
    else if (!std::strcmp(line, "mode primary")) command = {Operation::Mode, 0};
    else if (!std::strcmp(line, "mode reference")) command = {Operation::Mode, 1};
    else if (!std::strcmp(line, "mode dsp")) command = {Operation::Mode, 2};
    else if (!std::strcmp(line, "mode hybrid")) command = {Operation::Mode, 3};
    else if (!std::strcmp(line, "mute on")) command = {Operation::Mute, 1};
    else if (!std::strcmp(line, "mute off")) command = {Operation::Mute, 0};
    else if (!std::strcmp(line, "hold on")) command = {Operation::Hold, 1};
    else if (!std::strcmp(line, "hold off")) command = {Operation::Hold, 0};
    else if (!std::strcmp(line, "reset")) command = {Operation::Reset, 0};
    else if (!std::strncmp(line, "gain ", 5) && parse_number(line+5, 0, 1, value)) command = {Operation::Gain, value};
    else if (!std::strncmp(line, "delay ", 6) && parse_number(line+6, 0, 64, value)
        && value == std::floor(value)) command = {Operation::Delay, value};
    else valid = false;
    if (!valid) send_text("{\"error\":\"invalid command; type help\"}\n");
    else if (xQueueSend(command_queue, &command, 0) != pdTRUE) send_text("{\"error\":\"command queue full\"}\n");
    else send_text("{\"accepted\":true}\n");
}
void control_task(void*) {
    char line[96]; size_t used = 0;
    bool discard = false;
    Snapshot s;
    int64_t last_stats = 0;
    bool raw_button = true, stable_button = true, long_press_sent = false;
    int64_t button_changed = 0, button_pressed = 0;
    send_text("Mounam v2.0 | dual-mic neural enhancement | 16000 Hz | output MUTED | type help\n");
    for (;;) {
        xQueuePeek(snapshot_queue, &s, 0);
        CapturePacket packet;
        for (unsigned n = 0; n < 8 && xQueueReceive(capture_queue, &packet, 0) == pdTRUE; ++n) {
            if (capture_active()) uart_write_bytes(kUart, &packet, sizeof(packet));
        }
        uint8_t input[96];
        const int received = uart_read_bytes(kUart, input, sizeof(input), pdMS_TO_TICKS(1));
        for (int i = 0; i < received; ++i) {
            const char ch = char(input[i]);
            if (ch == '\r') continue;
            if (ch == '\n') {
                if (!discard) { line[used] = 0; if (used) handle_line(line, s); }
                else if (!capture_active()) send_text("{\"error\":\"command too long\"}\n");
                used = 0; discard = false;
            } else if (used+1 < sizeof(line) && !discard) line[used++] = ch;
            else discard = true;
        }
        const int64_t now = esp_timer_get_time();
        const bool level = gpio_get_level(GPIO_NUM_0) != 0;
        if (level != raw_button) { raw_button = level; button_changed = now; }
        if (now-button_changed > 30000 && stable_button != raw_button) {
            stable_button = raw_button;
            if (!stable_button) { button_pressed = now; long_press_sent = false; }
            else if (!long_press_sent && !s.fault) {
                const Command button = s.settings.muted ? Command{Operation::Demo, 0}
                    : Command{Operation::Mode, s.settings.mode == Mode::Primary ? 3.0f : 0.0f};
                xQueueSend(command_queue, &button, 0);
            }
        }
        if (!stable_button && !long_press_sent && now-button_pressed >= 1000000) {
            const Command mute{Operation::Mute, 1};
            xQueueSend(command_queue, &mute, 0); long_press_sent = true;
        }
        if (!capture_active() && now-last_stats > 1000000) { print_stats(s); last_stats = now; }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
}
extern "C" void app_main() {
    esp_log_level_set("*", ESP_LOG_NONE);
    ESP_ERROR_CHECK(esp_psram_is_initialized() ? ESP_OK : ESP_ERR_INVALID_STATE);
    // Neither Wi-Fi nor Bluetooth is initialized; no networking components are linked explicitly.
    uart_config_t uart{};
    uart.baud_rate = 921600; uart.data_bits = UART_DATA_8_BITS; uart.parity = UART_PARITY_DISABLE;
    uart.stop_bits = UART_STOP_BITS_1; uart.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    uart.source_clk = UART_SCLK_DEFAULT;
    ESP_ERROR_CHECK(uart_param_config(kUart, &uart));
    ESP_ERROR_CHECK(uart_driver_install(kUart, 2048, 8192, 0, nullptr, 0));
    command_queue = xQueueCreate(8, sizeof(Command));
    snapshot_queue = xQueueCreate(1, sizeof(Snapshot));
    capture_queue = xQueueCreate(8, sizeof(CapturePacket));
    ESP_ERROR_CHECK(command_queue && snapshot_queue && capture_queue ? ESP_OK : ESP_ERR_NO_MEM);
    initialize_audio();
    ESP_ERROR_CHECK(xTaskCreatePinnedToCore(audio_task, "audio", 8192, nullptr, 20, nullptr, 1) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(xTaskCreatePinnedToCore(control_task, "control", 6144, nullptr, 4, nullptr, 0) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}
