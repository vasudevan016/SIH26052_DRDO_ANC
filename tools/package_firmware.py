"""Assemble IDF's built flash regions into a verified image for one-command flashing."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "mounam-esp32s3-n16p8.bin"


def source_digest(root=ROOT):
    digest = hashlib.sha256()
    files = []
    for folder in (root/"components", root/"firmware"):
        for file in folder.rglob("*"):
            relative = file.relative_to(root)
            if not file.is_file() or any(p in {"build", "prebuilt", "__pycache__"} for p in relative.parts):
                continue
            if file.name in {"sdkconfig", "sdkconfig.old"}:
                continue
            if file.suffix not in {".c", ".cpp", ".h", ".hpp", ".S", ".ld"} and file.name not in {
                "CMakeLists.txt", "Kconfig", "Kconfig.projbuild", "sdkconfig.defaults", "idf_component.yml"}:
                continue
            files.append(file)
    for file in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        digest.update(file.relative_to(root).as_posix().encode()+b"\0")
        digest.update(file.read_bytes()+b"\0")
    return digest.hexdigest()


def package(build, output, source_commit, root=ROOT):
    build = build.resolve()
    args = json.loads((build/"flasher_args.json").read_text())
    if args["extra_esptool_args"]["chip"] != "esp32s3":
        raise ValueError("Expected ESP32-S3 build.")
    regions = []
    for address, name in args["flash_files"].items():
        file = (build/name).resolve()
        if not file.is_relative_to(build):
            raise ValueError("Flash source escapes build directory.")
        regions.append((int(address, 0), file.read_bytes(), name))
    regions.sort()
    if {r[0] for r in regions} != {0, 0x8000, 0x10000}:
        raise ValueError("Expected bootloader, partition table and factory app offsets.")
    image = bytearray(b"\xff"*max(address+len(raw) for address, raw, _ in regions))
    last_end = 0
    for address, raw, _ in regions:
        if address < last_end or address+len(raw) > 16*1024*1024:
            raise ValueError("Overlapping or out-of-range flash region.")
        image[address:address+len(raw)] = raw
        last_end = address+len(raw)
    if image[0] != 0xe9 or image[0x10000] != 0xe9:
        raise ValueError("Missing ESP image headers.")
    if int.from_bytes(image[12:14], "little") != 9:
        raise ValueError("Image chip identifier is not ESP32-S3.")
    output.mkdir(parents=True, exist_ok=True)
    (output/IMAGE).write_bytes(image)
    metadata = dict(board="ESP32-S3-WROOM-1-N16P8", chip="esp32s3", filename=IMAGE,
        flash_offset="0x0", flash_settings=args["flash_settings"], bytes=len(image),
        sha256=hashlib.sha256(image).hexdigest(), sources_sha256=source_digest(root),
        source_commit=source_commit, idf_version="v5.4.3",
        model_provenance=re.search(r'kProvenance = "([^"]+)"', (root/"components/mounam_dsp/include/model_weights.h").read_text()).group(1),
        note="CI-built; hardware timing and real speech quality need measurement.")
    (output/"manifest.json").write_text(json.dumps(metadata, indent=2)+"\n")
    return metadata


def verify(directory, root=ROOT):
    metadata = json.loads((directory/"manifest.json").read_text())
    if metadata.get("board") != "ESP32-S3-WROOM-1-N16P8" or metadata.get("filename") != IMAGE:
        raise ValueError("Wrong board or firmware filename.")
    image = directory/IMAGE
    raw = image.read_bytes()
    if len(raw) != metadata["bytes"] or hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise ValueError("Firmware checksum mismatch. Download the repository again.")
    if source_digest(root) != metadata["sources_sha256"]:
        raise ValueError("Firmware sources changed after this image was built. Rebuild or use an unchanged checkout.")
    if raw[0] != 0xe9 or int.from_bytes(raw[12:14], "little") != 9:
        raise ValueError("Not an ESP32-S3 firmware image.")
    return image, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=ROOT/"firmware/build")
    parser.add_argument("--output", type=Path, default=ROOT/"firmware/prebuilt")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        _, result = verify(args.output)
    else:
        commit = os.environ.get("MOUNAM_SOURCE_SHA") or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        result = package(args.build, args.output, commit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
