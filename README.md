# ArduPilot Firmware Utilities

Utilities for inspecting, packaging, signing, and uploading ArduPilot APJ firmware. The work was developed during an embedded-systems internship and focuses on repeatable tooling rather than generated firmware artifacts.

## Highlights

- Inspect APJ metadata and payload structure.
- Combine board-specific APJ files into an `APJPKGv1` bundle.
- Select firmware by board ID before calling the standard ArduPilot uploader.
- Generate signing keys for secure-boot experiments.
- Keep a custom CubeOrange+ bootloader hardware-definition file under version control.

## Repository layout

- `tools/apj-bundle/` — APJ inspection, bundle creation, and upload helpers.
- `secure-bootloader/` — key-generation utility and technical research notes.
- `hwdef/` — custom bootloader hardware-definition data.

Generated `.apj`, `.hex`, and `.bin` files are intentionally excluded. Signing keys must never be committed.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Each tool exposes its own command-line help:

```bash
python tools/apj-bundle/apj_analyze.py --help
python tools/apj-bundle/build_bundle.py --help
python tools/apj-bundle/smart_upload.py --help
```

The smart uploader requires the path to ArduPilot's standard `uploader.py`:

```bash
python tools/apj-bundle/smart_upload.py \
  --uploader /path/to/ardupilot/Tools/scripts/uploader.py \
  --port COM10 \
  universal_firmware.apj
```

You can also set `ARDUPILOT_UPLOADER` instead of passing `--uploader` every time.

## Safety notes

- Validate board IDs and firmware compatibility before flashing hardware.
- Keep private signing keys outside the repository and backed up securely.
- Test bootloader changes on recoverable development hardware first.

## Documentation

The repository retains the original Turkish engineering notes in `tools/apj-bundle/` and `secure-bootloader/` for implementation context.
