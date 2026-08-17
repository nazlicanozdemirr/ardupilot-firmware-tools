"""
Standart ArduPilot .apj dosyalarini tek bir kapsayici JSON'da birlestirir.

GENEL KULLANIM / KILAVUZ
------------------------

1) Bu script NE YAPIYOR?
   - Girdi olarak bir veya daha fazla TEK-KART .apj dosyasi alir
     (her biri ArduPilot'un normal JSON .apj formati).
   - Her dosyanin icerigini JSON olarak okur:
       board_id, image, image_size, summary, version, ...
   - Hepsini tek bir APJPKGv1 kapsayici JSON icine koyar:

       {
         "magic": "APJPKGv1",
         "format_version": 1,
         "description": "Tum filo icin evrensel paket",
         "version": "4.7.0",
         "firmwares": {
           "1063": { ... arduplane.apj JSON ... },
           "53":   { ... arduplane (1).apj JSON ... }
         }
       }

   - Bu kapsayici daha sonra smart_upload.py / entegre uploader tarafindan
     board_id'ye gore dogru ic kaydi secmek icin kullanilir.

2) TEMEL KULLANIM (iki kart ornegi)

   python create_fat_apj.py -o universal_firmware_4.7.0.apj ^
       "C:\\Users\\PC_2255\\Desktop\\nazli\\.apj_proje_dosyaları\\arduplane.apj" ^
       "C:\\Users\\PC_2255\\Desktop\\nazli\\.apj_proje_dosyaları\\arduplane (1).apj"

   - Ciktida her .apj icin board_id ve summary yazilir
   - Son satirlarda kapsayicinin yolu, format_version, version ve firmware sayisi gorunur.

3) ILERIDE YENI KART EKLERKEN NE YAPACAGIM?

   a) Oncelikle yeni kart icin normal ArduPilot .apj build et
      (ornegin arduplane_yeni_kart.apj gibi).

   b) Yeni .apj'nin icindeki board_id'yi kontrol etmek icin:

        python apj_analyze.py "C:\\...\\arduplane_yeni_kart.apj"

      - ciktida `board_id : ...` ve `summary : ...` satirlarini not al.

   c) create_fat_apj.py'yi yeni .apj'yi de dahil ederek tekrar calistir:

        python create_fat_apj.py -o universal_firmware_4.7.1.apj ^
            "....\\arduplane.apj" ^
            "....\\arduplane (1).apj" ^
            "....\\arduplane_yeni_kart.apj"

      - Eger ayni board_id iki farkli dosyada varsa, script HATA verir:
          "Ayni board_id icin birden fazla .apj var"
        Bu durumda ya yanlis .apj'yi cikart, ya da build tarafinda
        APJ_BOARD_ID ayarlarini duzelt.

4) YALNIZCA BIR KARTI GUNCELLEDIGINDE NE YAPACAGIM?

   - Ornegin sadece CubeOrangePlus icin yeni .apj aldiginda:
     1) Eski universal_firmware_*.apj'yi kullanma.
     2) create_fat_apj.py'yi tum kartlarin GUNCEL .apj'leriyle tekrar calistir:

          python create_fat_apj.py -o universal_firmware_4.7.2.apj ^
              "...\\son_arduplane_cubeorange.apj" ^
              "...\\mevcut_arduplane_pixhawk6x.apj"

   - Boylece paket icindeki tum kartlar ayni versiyon ailesinden gelir.

5) VERSIYON ALANI

   - `--version` parametresi verilmezse default "4.7.0" kullanilir.
   - Yeni release cikardiginda (4.7.1, 4.7.2, ...):
       ya komutta `--version 4.7.1` ver,
       ya da bu dosyada default degeri guncelle.

6) TIPIK HATA MESAJLARI

   - "Dosya bulunamadi: ..."       -> Yol yanlis; .apj dosyasinin yolunu kontrol et.
   - "magic != 'APJFWv1' ..."      -> Bu dosya ArduPilot .apj degil (yanlis dosya).
   - "board_id alani yok"         -> Uyumlu .apj degil / bozuk dosya.
   - "Ayni board_id icin birden..."-> Iki farkli dosyada ayni board_id var;
                                      build ayarlarini veya listeyi duzelt.

Bu kilavuz ileride yeni kart eklerken ne yapacagini hatirlaman icin
burada duruyor. Asil calisan kod, bu yorumun altindaki fonksiyonlardir.
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, List


MAGIC = "APJPKGv1"
FORMAT_VERSION = 1


def load_single_apj(path: str) -> Dict[str, Any]:
  """Tek kartlik standart .apj JSON'unu yukler ve temel alanlari dogrular."""
  try:
    with open(path, "r", encoding="utf-8") as f:
      data = json.load(f)
  except Exception as e:
    print(f"JSON okunamadi: {path} ({e})", file=sys.stderr)
    raise

  if not isinstance(data, dict):
    raise ValueError(f".apj beklenenden farkli tipte (dict degil): {path}")

  if data.get("magic") != "APJFWv1":
    raise ValueError(f"magic != 'APJFWv1' ({data.get('magic')!r}) dosya: {path}")

  if "board_id" not in data:
    raise ValueError(f"board_id alanı yok: {path}")
  if "image" not in data or "image_size" not in data:
    raise ValueError(f"image / image_size alanlari eksik: {path}")

  return data


def build_package(apj_paths: List[str], description: str, version: str) -> Dict[str, Any]:
  """Verilen .apj dosyalarindan APJPKGv1 kapsayici JSON nesnesi olusturur."""
  firmwares: Dict[str, Any] = {}

  for p in apj_paths:
    norm = os.path.normpath(p)
    if not os.path.isfile(norm):
      raise FileNotFoundError(f"Dosya bulunamadi: {norm}")
    data = load_single_apj(norm)
    board_id = data.get("board_id")
    key = str(board_id)
    if key in firmwares:
      raise ValueError(f"Ayni board_id icin birden fazla .apj var: {board_id} (eski: {firmwares[key].get('summary')!r}, yeni: {data.get('summary')!r})")
    firmwares[key] = data
    print(f"  board_id={board_id}  summary={data.get('summary')!r}  ->  {norm}")

  pkg: Dict[str, Any] = {
    "magic": MAGIC,
    "format_version": FORMAT_VERSION,
    "description": description,
    "version": version,
    "firmwares": firmwares,
  }
  return pkg


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Birden fazla standart .apj'yi tek APJPKGv1 kapsayici dosyada birlestir."
  )
  parser.add_argument(
    "-o",
    "--output",
    required=True,
    help="Cikis kapsayici dosya yolu (ornek: universal_firmware.apj)",
  )
  parser.add_argument(
    "--description",
    default="Tum filo icin evrensel firmware paketi",
    help="Kapsayici icin aciklama metni",
  )
  parser.add_argument(
    "--version",
    default="4.7.0",
    help="Kapsayici paket versiyonu (string)",
  )
  parser.add_argument(
    "inputs",
    nargs="+",
    help="Tek kartlik standart .apj dosyalari (tam yol veya goreli)",
  )
  args = parser.parse_args()

  try:
    pkg = build_package(args.inputs, description=args.description, version=args.version)
  except Exception as e:
    print("Paket olusturulamadi:", e, file=sys.stderr)
    sys.exit(1)

  out_path = os.path.normpath(args.output)
  try:
    with open(out_path, "w", encoding="utf-8") as f:
      json.dump(pkg, f, indent=2, ensure_ascii=False)
  except Exception as e:
    print(f"Cikis dosyasi yazilamadi: {out_path} ({e})", file=sys.stderr)
    sys.exit(1)

  print(f"\nAPJPKGv1 kapsayici yazildi: {out_path}")
  print(f"  magic          = {MAGIC}")
  print(f"  format_version = {FORMAT_VERSION}")
  print(f"  version        = {args.version}")
  print(f"  firmware sayisi= {len(pkg['firmwares'])}")


if __name__ == "__main__":
  main()

