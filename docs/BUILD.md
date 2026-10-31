# Developer build (optional)

For simply flashing your ESP, use `bash flash.sh` from the repository root. This
page is needed only when modifying the firmware or deploying new model weights.

## Install ESP-IDF once on Ubuntu

```bash
sudo apt update
sudo apt install -y git wget flex bison gperf python3 python3-pip python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0 build-essential
mkdir -p "$HOME/esp"
git clone --branch v5.4.3 --recursive https://github.com/espressif/esp-idf.git "$HOME/esp/esp-idf-v5.4.3"
cd "$HOME/esp/esp-idf-v5.4.3"
./install.sh esp32s3
```

## Rebuild after source/model changes

From the repository root, in a fresh terminal:

```bash
. "$HOME/esp/esp-idf-v5.4.3/export.sh"
cd firmware
idf.py set-target esp32s3
python ../tools/check_sdkconfig.py sdkconfig
idf.py build
cd ..
python -m tools.package_firmware
bash flash.sh
```

The SDK Python environment builds/packages; the flashing script manages its own
small environment. Generated images carry the source fingerprint, so modifying
firmware/components requires a rebuild before normal flashing. If an SDK with
that path already exists, verify `idf.py --version` before using it.

For host DSP tests/training, use a separate terminal from the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make test
make benchmark
```

`make benchmark` measures the host machine, not ESP32 latency. Live device stats
and GPIO10 provide the DSP processing measurement on your board. Whole acoustic
latency includes converter/buffering delays and needs separate instrumentation.
