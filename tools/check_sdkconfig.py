"""Reject a successful-looking build that silently discarded required N16P8 defaults."""
import sys
from pathlib import Path


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("firmware/sdkconfig")
    required = {
        'CONFIG_IDF_TARGET="esp32s3"',
        "CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y",
        "CONFIG_SPIRAM=y",
        "CONFIG_SPIRAM_MODE_OCT=y",
        "CONFIG_SPIRAM_SPEED_80M=y",
        "CONFIG_SPIRAM_BOOT_INIT=y",
        "CONFIG_SPIRAM_USE_MALLOC=y",
        "CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ=240",
        "CONFIG_FREERTOS_HZ=1000",
        "CONFIG_ESP_CONSOLE_UART_CUSTOM=y",
        "CONFIG_ESP_CONSOLE_UART_NUM=0",
        "CONFIG_ESP_CONSOLE_UART_TX_GPIO=43",
        "CONFIG_ESP_CONSOLE_UART_RX_GPIO=44",
        "CONFIG_ESP_CONSOLE_UART_BAUDRATE=921600",
    }
    actual = set(path.read_text().splitlines())
    missing = sorted(required-actual)
    if missing:
        raise SystemExit("Required N16P8 configuration missing:\n"+"\n".join(missing))
    print("Verified ESP32-S3, 16 MB flash, octal 80 MHz PSRAM, 240 MHz CPU and UART configuration.")


if __name__ == "__main__":
    main()
