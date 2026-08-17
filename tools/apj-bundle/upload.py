"""
Tak-calistir: Tek .apj bundle dosyasindan kart tipine gore dogru image'i secip yukler.

Kullanim:
  python upload.py firmware.apj --board-id 140 -p COM10
  python upload.py firmware.apj --board-id 140 -p COM10 -b 115200

Board ID'yi komut satirinda veriyorsunuz (hangi karti taktiginizi siz biliyorsunuz).
Bundle icinde o board_id icin image yoksa hata verir.
Mevcut host_flasher (cursor.bootloader) kullanilarak sadece o image yuklenir.
"""

import argparse
import os
import subprocess
import sys
import tempfile

# cursor.apj icinden calistigimizda bir ust dizindeki cursor.bootloader'daki host_flasher kullanilir
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOTLOADER_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "cursor.bootloader")
HOST_FLASHER = os.path.join(BOOTLOADER_DIR, "host_flasher.py")

from apj_bundle import get_image_for_board


def main():
    parser = argparse.ArgumentParser(
        description="APJ bundle'dan board_id'ye gore image secip STM32'ye yukler (tak-calistir)."
    )
    parser.add_argument("apj_file", help="Icinde birden fazla kart image'i olan .apj bundle dosyasi")
    parser.add_argument("--board-id", "-B", type=int, required=True,
                        help="Takili kartin board ID'si (orn. 140)")
    parser.add_argument("-p", "--port", default="COM10", help="Seri port (varsayilan: COM10)")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud (varsayilan: 115200)")
    parser.add_argument("--force", action="store_true", help="MD5 atla, her zaman yukle (host_flasher'a iletilir)")
    args = parser.parse_args()

    if not os.path.isfile(args.apj_file):
        print("APJ dosyasi bulunamadi:", args.apj_file, file=sys.stderr)
        sys.exit(1)

    image = get_image_for_board(args.apj_file, args.board_id)
    if image is None:
        print("Bundle'da board_id=%s icin image yok." % args.board_id, file=sys.stderr)
        print("Desteklenen board_id'leri gormek icin: python build_bundle.py --list <apj_file>", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(HOST_FLASHER):
        print("host_flasher bulunamadi:", HOST_FLASHER, file=sys.stderr)
        print("cursor.bootloader klasorunun bir ust dizinde oldugundan emin olun.", file=sys.stderr)
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(image)
        tmp_path = tmp.name

    try:
        cmd = [sys.executable, HOST_FLASHER, tmp_path, "-p", args.port, "-b", str(args.baud)]
        if args.force:
            cmd.append("--force")
        print("Board ID %s icin image yukleniyor (%s byte)..." % (args.board_id, len(image)))
        r = subprocess.run(cmd, cwd=BOOTLOADER_DIR)
        if r.returncode != 0:
            sys.exit(r.returncode)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    print("upload.py tamamlandi.")


if __name__ == "__main__":
    main()
