"""
APJ Bundle (.apj) okuyucu.
Tek dosyada board_id'ye göre image saklayan kapsayıcı format.
"""
import struct
from typing import Dict, Optional, Tuple

APJ_MAGIC = b"APJB"
APJ_VERSION = 1


def parse_apj_bundle(path: str) -> Dict[int, bytes]:
    """
    .apj dosyasını açar; board_id -> image_data (bytes) sözlüğü döner.
    Aynı board_id birden fazla görünürse son gelen geçerli olur.
    """
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 8:
        raise ValueError(f"APJ dosyasi cok kisa: {path}")
    magic = data[:4]
    if magic != APJ_MAGIC:
        raise ValueError(f"Gecersiz APJ dosyasi (magic '{magic!r}' beklenen '{APJ_MAGIC!r}'): {path}")
    version = struct.unpack_from("<H", data, 4)[0]
    if version != APJ_VERSION:
        raise ValueError(f"Bilinmeyen APJ versiyonu {version}, desteklenen: {APJ_VERSION}")
    num_images = struct.unpack_from("<H", data, 6)[0]
    result = {}
    offset = 8
    for _ in range(num_images):
        if offset + 8 > len(data):
            break
        board_id = struct.unpack_from("<I", data, offset)[0]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
        if offset + size > len(data):
            break
        result[board_id] = data[offset:offset + size]
        offset += size
    return result


def get_image_for_board(apj_path: str, board_id: int) -> Optional[bytes]:
    """Bundle'dan verilen board_id için image'ı döndürür; yoksa None."""
    images = parse_apj_bundle(apj_path)
    return images.get(board_id)
