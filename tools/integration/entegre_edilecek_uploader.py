"""
KENDI UPLOADER'INA YAPIŞTIRACAĞIN MINIMAL KISIM
===============================================

1) Kendi uploader dosyanın EN ÜSTÜNE (import'lardan sonra) şu blokları ekle.
2) Argparse'a bir seçenek ekle: --fat-package veya firmware argümanı .apj ise
   dosyayı açıp magic "APJPKGv1" var mı diye bak (aşağıdaki is_fat_package ile).
3) main() içinde, firmware dosyası belli olduktan SONRA ve gerçek yükleme
   döngüsüne girmeden ÖNCE şu if'i ekle (örnek aşağıda).

Gerekli import'lar (zaten yoksa ekle):
  import json
  import os
  import re
  import subprocess
  import sys
  import tempfile
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict

# --- Fat APJ sabitleri ---
FAT_MAGIC = "APJPKGv1"


def _is_fat_package(path: str) -> bool:
    """Dosya APJPKGv1 kapsayıcısı mı (ilk 200 byte'ta magic var mı)."""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(200)
        return FAT_MAGIC in head
    except Exception:
        return False


def _read_board_id_identify(port: str, uploader_script: str) -> int:
    """uploader_script'i --port PORT --identify ile çalıştırır, stdout'tan board_type: NNN parse eder."""
    cmd = [sys.executable, uploader_script, "--port", port, "--identify"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"identify basarisiz (kod {result.returncode}): {result.stderr or ''}")
    m = re.search(r"board_type:\s*(\d+)", result.stdout or "")
    if not m:
        raise RuntimeError("identify cikisinda 'board_type: <sayi>' bulunamadi.")
    return int(m.group(1))


def _load_fat_package(path: str) -> Dict[str, Any]:
    """APJPKGv1 kapsayıcıyı yükler."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("magic") != FAT_MAGIC:
        raise ValueError("Gecersiz veya APJPKGv1 degil.")
    if not isinstance(data.get("firmwares"), dict) or not data["firmwares"]:
        raise ValueError("firmwares bos veya yok.")
    return data


def select_firmware_from_fat_package(
    port: str,
    package_path: str,
    uploader_script: str,
) -> str:
    """
    Fat paketten kartı otomatik seçip seçilen tek .apj'yi geçici dosyaya yazar.
    Dönen değer: geçici .apj dosyasının yolu. Çağıran bu dosyayı yükleme bitince silmeli.
    """
    pkg = _load_fat_package(package_path)
    board_id = _read_board_id_identify(port, uploader_script)
    key = str(board_id)
    if key not in pkg["firmwares"]:
        raise KeyError(f"Pakette board_id={board_id} yok.")
    fw = pkg["firmwares"][key]
    if not isinstance(fw, dict):
        raise ValueError(f"firmwares[{key}] dict degil.")
    fd, temp_path = tempfile.mkstemp(suffix=".apj")
    os.close(fd)
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(fw, f, indent=2, ensure_ascii=False)
    return temp_path


# =============================================================================
# KENDI MAIN'INE EKLENECEK ÖRNEK (uploader'ının firmware yükleme döngüsünden ÖNCE)
# =============================================================================
#
#   # firmware dosyası args.firmware veya benzeri bir değişkende varsayalım
#   firmware_path = args.firmware  # veya senin arg adın
#   temp_apj_from_fat = None
#
#   if _is_fat_package(firmware_path):
#       uploader_script = os.path.abspath(__file__)  # kendi uploader'ın
#       firmware_path = select_firmware_from_fat_package(
#           args.port, firmware_path, uploader_script
#       )
#       temp_apj_from_fat = firmware_path
#       print("Fat paketten secilen firmware:", firmware_path)
#
#   try:
#       # Buradan sonra mevcut yükleme kodun (firmware_path kullan)
#       # ornek: fw = firmware(firmware_path)
#       #        ... upload döngüsü ...
#       pass
#   finally:
#       if temp_apj_from_fat and os.path.isfile(temp_apj_from_fat):
#           try:
#               os.unlink(temp_apj_from_fat)
#           except Exception:
#               pass
#
# =============================================================================
