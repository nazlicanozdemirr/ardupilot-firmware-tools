"""
APJPKGv1 kapsayici dosyadan dogru tek-kart .apj'yi secip standart uploader.py'a veren wrapper.

Kullanim (ornek):

  python smart_upload.py --port COM10 universal_firmware.apj

Akis:
  1) Cihazin board_id'sini otomatik okumaya calisir.
     - Bunu yapmak icin mevcut uploader.py'yi `--identify` modunda calistirir,
       stdout'tan `board_type: 1063` satirini parse eder.
     - Boylece bootloader'a ekstra komut eklemeden kartin board_id'si ogrenilir.
     - Otomatik okuma basarili olmazsa, --board-id ile manuel verebilirsin.
  2) APJPKGv1 kapsayici JSON'u acar, firmwares[str(board_id)] kaydini bulur.
  3) Bu ic kaydi gecici bir .apj dosyasina yazar.
  4) Mevcut uploader.py script'ini bu gecici .apj ile cagirir.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict


PKG_MAGIC = "APJPKGv1"
PKG_FORMAT_VERSION = 1


def read_board_id_via_uploader(port: str, uploader_script: str) -> int:
  """
  Mevcut uploader.py'yi `--identify` modunda calistirarak board_id (board_type) okur.

  stdout icerisinde su satiri arar:
    board_type: 1063
  ve 1063 degerini dondurur.
  """
  if not os.path.isfile(uploader_script):
    raise RuntimeError(f"uploader.py bulunamadi: {uploader_script}")

  cmd = [sys.executable, uploader_script, "--port", port, "--identify"]
  print(
    "Board ID otomatik okuma icin calistirilan komut:",
    " ".join(f'"{c}"' if " " in c else c for c in cmd),
  )
  try:
    result = subprocess.run(cmd, capture_output=True, text=True)
  except Exception as e:
    raise RuntimeError(f"uploader.py --identify calistirilamadi: {e}")

  if result.returncode != 0:
    stderr = (result.stderr or "").strip()
    raise RuntimeError(
      f"uploader.py --identify cikis kodu {result.returncode}. stderr: {stderr}"
    )

  out = result.stdout or ""
  m = re.search(r"board_type:\s*(\d+)", out)
  if not m:
    raise RuntimeError("uploader.py --identify cikisinda 'board_type' satiri bulunamadi.")

  bid = int(m.group(1))
  return bid


def load_package(path: str) -> Dict[str, Any]:
  """APJPKGv1 kapsayiciyi yukler ve dogrular."""
  with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
  if not isinstance(data, dict):
    raise ValueError("Kapsayici JSON dict degil.")
  if data.get("magic") != PKG_MAGIC:
    raise ValueError(f"magic={data.get('magic')!r}, beklenen {PKG_MAGIC!r}")
  if int(data.get("format_version", -1)) != PKG_FORMAT_VERSION:
    raise ValueError(f"format_version={data.get('format_version')}, beklenen {PKG_FORMAT_VERSION}")
  firmwares = data.get("firmwares")
  if not isinstance(firmwares, dict) or not firmwares:
    raise ValueError("firmwares dict yok veya bos.")
  return data


def pick_firmware(pkg: Dict[str, Any], board_id: int) -> Dict[str, Any]:
  """Verilen board_id icin ic .apj kaydini secer."""
  firmwares = pkg.get("firmwares", {})
  key = str(board_id)
  if key not in firmwares:
    raise KeyError(f"Kapsayici icinde board_id={board_id} icin firmware yok.")
  fw = firmwares[key]
  if not isinstance(fw, dict):
    raise ValueError(f"firmwares[{key!r}] dict degil.")
  return fw


def run_uploader(temp_apj_path: str, port: str, uploader_script: str) -> int:
  """uploader.py script'ini verilen .apj ve port ile calistirir."""
  if not os.path.isfile(uploader_script):
    print(f"uploader.py bulunamadi: {uploader_script}", file=sys.stderr)
    return 1

  cmd = [sys.executable, uploader_script, "--port", port, temp_apj_path]
  print("Calistirilan komut:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
  try:
    r = subprocess.run(cmd)
  except Exception as e:
    print(f"uploader.py calistirilamadi: {e}", file=sys.stderr)
    return 1
  return r.returncode


def main() -> None:
  parser = argparse.ArgumentParser(
    description="APJPKGv1 kapsayicidan dogru .apj'yi secip standart uploader.py ile yukleyen akilli wrapper."
  )
  parser.add_argument(
    "--port",
    required=True,
    help="Bootloader'a baglanilacak seri port (orn. COM10 veya /dev/ttyACM0)",
  )
  parser.add_argument(
    "--board-id",
    type=int,
    help="Board ID'yi elle belirt (otomatik okumayi bypass eder).",
  )
  parser.add_argument(
    "--uploader",
    default=os.environ.get("ARDUPILOT_UPLOADER"),
    help="ArduPilot uploader.py yolu (veya ARDUPILOT_UPLOADER ortam degiskeni)",
  )
  parser.add_argument(
    "package",
    help="APJPKGv1 kapsayici dosya (universal_firmware.apj gibi)",
  )
  args = parser.parse_args()

  if not args.uploader:
    parser.error("--uploader gerekli (alternatif: ARDUPILOT_UPLOADER)")
  uploader_script = os.path.abspath(os.path.expanduser(args.uploader))

  pkg_path = os.path.normpath(args.package)
  if not os.path.isfile(pkg_path):
    print("Kapsayici dosya bulunamadi:", pkg_path, file=sys.stderr)
    sys.exit(1)

  try:
    pkg = load_package(pkg_path)
  except Exception as e:
    print("Kapsayici okunamadi / gecersiz:", e, file=sys.stderr)
    sys.exit(1)

  # 1) Board ID'yi belirle
  if args.board_id is not None:
    board_id = args.board_id
    print(f"Board ID manuel verildi: {board_id}")
  else:
    try:
      board_id = read_board_id_via_uploader(args.port, uploader_script)
      print(f"Uploader identify ile okunan Board ID: {board_id}")
    except Exception as e:
      print("Board ID otomatik okunamadi:", e, file=sys.stderr)
      print("Tekrar deneyebilir veya --board-id ile elle verebilirsin.", file=sys.stderr)
      sys.exit(1)

  # 2) Kapsayicidan ilgili .apj kaydini sec
  try:
    fw_entry = pick_firmware(pkg, board_id)
  except Exception as e:
    print("Kapsayicidan firmware secilemedi:", e, file=sys.stderr)
    sys.exit(1)

  # 3) Gecici .apj yaz
  with tempfile.NamedTemporaryFile(suffix=".apj", delete=False) as tmp:
    temp_apj_path = tmp.name
  try:
    with open(temp_apj_path, "w", encoding="utf-8") as f:
      json.dump(fw_entry, f, indent=2, ensure_ascii=False)
    print(f"Gecici .apj olusturuldu: {temp_apj_path}")

    # 4) uploader.py'i bu dosya ile calistir
    rc = run_uploader(temp_apj_path, args.port, uploader_script)
  finally:
    try:
      os.unlink(temp_apj_path)
      print(f"Gecici .apj silindi: {temp_apj_path}")
    except Exception:
      pass

  if rc != 0:
    print(f"Yukleme basarisiz (uploader cikis kodu {rc}).", file=sys.stderr)
    sys.exit(rc)

  print("Yukleme basarili.")


if __name__ == "__main__":
  main()

