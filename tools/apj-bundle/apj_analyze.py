"""
ArduPilot APJ dosyasinin analizi.

Gercek APJ formatı: JSON. Ana alanlar:
  - board_id     : Kart tipi kimligi (orn. 140)
  - magic        : "APJFWv1"
  - description  : Aciklama
  - image        : zlib ile sikistirilmis + base64 ile kodlanmis firmware
  - image_size   : zlib decompress sonrasi boyut (byte)
  - summary, version, flash_total, git_identity, USBID, ...
"""
import argparse
import base64
import json
import os
import sys
import zlib


def analyze(apj_path: str, save_image: bool = False) -> None:
    with open(apj_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    print("=" * 60)
    print("APJ ANALIZ:", os.path.basename(apj_path))
    print("=" * 60)
    print("board_id     :", d.get("board_id"))
    print("magic        :", d.get("magic"))
    print("description  :", d.get("description"))
    print("summary      :", d.get("summary"))
    print("version      :", d.get("version"))
    print("image_size   :", d.get("image_size"), "byte")
    print("image_maxsize:", d.get("image_maxsize"), "byte")
    print("flash_total  :", d.get("flash_total"), "byte")
    print("flash_free   :", d.get("flash_free"))
    print("git_identity :", d.get("git_identity"))
    print("board_revision:", d.get("board_revision"))
    print("USBID        :", d.get("USBID"))
    if "extf_image_size" in d and d["extf_image_size"]:
        print("extf_image_size:", d.get("extf_image_size"))
    print()

    image_b64 = d.get("image")
    if not image_b64:
        print("'image' (base64) yok.")
        return

    decoded = base64.b64decode(image_b64)
    try:
        raw = zlib.decompress(decoded)
    except zlib.error:
        raw = decoded  # bazi eski apj'ler sadece base64 olabilir
    print("Image (base64+zlib decode sonrasi):", len(raw), "byte")
    if d.get("image_size") is not None:
        print("image_size (apj'deki):", d["image_size"], "byte")
    if len(raw) >= 8:
        print("Ilk 8 byte (hex):", raw[:8].hex())
        print("Ilk 4 byte (SP/Reset vektor olabilir):", raw[:4].hex())
    print()

    if save_image:
        out_name = os.path.splitext(apj_path)[0] + "_image.bin"
        with open(out_name, "wb") as f:
            f.write(raw)
        print("Image kaydedildi:", out_name)


def main():
    parser = argparse.ArgumentParser(description="ArduPilot APJ dosyasi analizi (JSON format).")
    parser.add_argument("apj_file", help=".apj dosyasi (JSON)")
    parser.add_argument("--save-image", action="store_true", help="image alanini .bin olarak kaydet")
    args = parser.parse_args()

    if not os.path.isfile(args.apj_file):
        print("Dosya bulunamadi:", args.apj_file, file=sys.stderr)
        sys.exit(1)

    analyze(args.apj_file, save_image=args.save_image)


if __name__ == "__main__":
    main()
