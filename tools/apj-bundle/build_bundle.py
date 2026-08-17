"""
APJ bundle olusturur veya mevcut .apj icerigini listeler.

Bundle olusturma:
  python build_bundle.py -o firmware.apj 140:kart140.bin 141:kart141.bin
  python build_bundle.py -o firmware.apj 140:build/app_140.bin 141:build/app_141.bin

Icerik listeleme:
  python build_bundle.py --list firmware.apj
"""

import argparse
import os
import struct
import sys

APJ_MAGIC = b"APJB"
APJ_VERSION = 1


def load_bin(path):
    with open(path, "rb") as f:
        return f.read()


def load_hex(path):
    try:
        from intelhex import IntelHex
    except ImportError:
        raise RuntimeError(" .hex icin: pip install intelhex")
    APP_START = 0x08008000
    APP_MAX_SIZE = 480 * 1024
    ih = IntelHex(path)
    try:
        end = ih.maxaddr()
    except Exception:
        return None
    if end < APP_START:
        return None
    start = max(ih.minaddr(), APP_START)
    end = min(end, APP_START + APP_MAX_SIZE - 1)
    return ih.tobinstr(start=start, end=end)


def build_bundle(output_path, entries):
    """
    entries: [(board_id int, image_bytes bytes), ...]
    """
    with open(output_path, "wb") as f:
        f.write(APJ_MAGIC)
        f.write(struct.pack("<H", APJ_VERSION))
        f.write(struct.pack("<H", len(entries)))
        for board_id, data in entries:
            f.write(struct.pack("<I", board_id))
            f.write(struct.pack("<I", len(data)))
            f.write(data)
    print("Yazildi: %s (%s image)" % (output_path, len(entries)))


def list_bundle(apj_path):
    from apj_bundle import parse_apj_bundle
    images = parse_apj_bundle(apj_path)
    if not images:
        print("Bundle bos veya gecersiz.")
        return
    print("Board ID  |  Size (byte)")
    print("----------+-------------")
    for bid in sorted(images.keys()):
        print("%9u | %s" % (bid, len(images[bid])))


def main():
    parser = argparse.ArgumentParser(description="APJ bundle olustur veya listele.")
    parser.add_argument("-o", "--output", help="Cikacak .apj dosyasi (olusturma modu)")
    parser.add_argument("--list", dest="list_file", metavar="APJ_FILE", help="Mevcut .apj icerigini listele")
    parser.add_argument("entries", nargs="*", help="board_id:dosya.bin veya board_id:dosya.hex (olusturma modunda)")
    args = parser.parse_args()

    if args.list_file:
        if not os.path.isfile(args.list_file):
            print("Dosya bulunamadi:", args.list_file, file=sys.stderr)
            sys.exit(1)
        list_bundle(args.list_file)
        return

    if not args.output or not args.entries:
        parser.print_help()
        print("\nOrnek: python build_bundle.py -o firmware.apj 140:app_140.bin 141:app_141.bin")
        sys.exit(1)

    entries = []
    for spec in args.entries:
        if ":" not in spec:
            print("Hatali giris (board_id:dosya olmali):", spec, file=sys.stderr)
            sys.exit(1)
        bid_str, path = spec.split(":", 1)
        try:
            board_id = int(bid_str)
        except ValueError:
            print("board_id tamsayi olmali:", bid_str, file=sys.stderr)
            sys.exit(1)
        if not os.path.isfile(path):
            print("Dosya bulunamadi:", path, file=sys.stderr)
            sys.exit(1)
        if path.lower().endswith(".hex"):
            data = load_hex(path)
        else:
            data = load_bin(path)
        if not data:
            print("Dosya okunamadi veya bos:", path, file=sys.stderr)
            sys.exit(1)
        entries.append((board_id, data))
        print("  board_id %s -> %s (%s byte)" % (board_id, path, len(data)))

    build_bundle(args.output, entries)


if __name__ == "__main__":
    main()
