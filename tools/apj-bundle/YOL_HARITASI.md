# APJ Tak-Çalıştır Projesi – İlerleme Planı

## Hedef
Tek bir .apj dosyası (veya tek bir “paket”) + kartı takınca **board_id’yi cihazdan öğrenip** doğru firmware’i seçip yükleyen tak-çalıştır akışı.

---

## Şu anki durum

| Parça | Durum | Not |
|-------|--------|-----|
| **Bundle formatı** | Var (2 tür) | 1) Kendi binary formatımız (APJB), 2) ArduPilot JSON .apj (tek kart) |
| **upload.py** | Var | `--board-id` ile bundle’dan image seçip yüklüyor; şu an **eski host_flasher**’a (cursor.bootloader) bağımlı |
| **Board ID kaynağı** | Manuel | Komut satırında `--board-id` veriyorsun; cihazdan otomatik okuma yok |
| **Yükleme protokolü** | Eski projeye bağlı | Yeni projede kendi bootloader/yükleme protokolün tanımlanacak |

---

## Nasıl ilerlemeliyiz (adımlar)

### 1. Format kararı (tek tip veya ikisini destekle)
- **Seçenek A:** Sadece **kendi bundle formatımız (APJB)** – `build_bundle.py` ile üretilen tek dosya, birden fazla board_id.
- **Seçenek B:** **ArduPilot JSON .apj** ile uyumlu ol – tek kartlı .apj’leri okuyabilen + istersen “çoklu kart” için ya birden fazla .apj dosyası ya da tek JSON içinde birden fazla image.
- **Seçenek C:** İkisini de destekle: upload.py hem APJB hem ArduPilot .apj (veya sadece board_id + image içeren basit JSON) okusun; dosya uzantısı/magic’e göre otomatik seçsin.

**Öneri:** Önce **C** – hem mevcut APJB hem ArduPilot örnek .apj ile test edebilirsin; sonra tek formatta toplayabilirsin.

---

### 2. Board ID’yi cihazdan alma (otomatik tak-çalıştır)
- Kartta çalışan bir **bootloader** (veya özel bir “kimlik modu”) olacak.
- PC’deki upload aracı (upload.py) seri/USB’den **“board_id nedir?”** komutunu gönderecek; cihaz **board_id** (örn. 140) döndürecek.
- Bu komut/protokol **yeni projeye ait**; eski bootloader kodu kullanılmayacak.

**Yapılacaklar:**
- Protokolü netleştir: komut kodu (örn. `GET_BOARD_ID`), yanıt formatı (örn. 4 byte little-endian board_id).
- Bootloader tarafında bu komutu işleyen kod (yeni projede).
- upload.py içinde: port aç → GET_BOARD_ID gönder → board_id oku → bundle’dan image seç → yükleme adımına geç.

---

### 3. Yükleme protokolü (flash yazma)
- Eski projedeki host_flasher’a **bağımlılığı kaldır**: yeni projede kendi “flasher” mantığın olsun.
- Bootloader’da olması gerekenler:  
  - Cihaz resetlenince veya özel modda **UART/USB’den komut bekle**.  
  - Komutlar: **GET_BOARD_ID**, **ERASE**, **WRITE_CHUNK**, **VERIFY/END** (veya tek komutla “şu adrese şu veriyi yaz”).  
- upload.py tarafında: seçilen image’ı parça parça gönderip erase + write + (isteğe göre) verify.

**Yapılacaklar:**
- Yeni proje için bootloader spesifikasyonu (hangi komutlar, paket formatı, CRC vb.).
- Bootloader firmware’i (C/ARM) – sadece bu projeye özel.
- upload.py içinde “flasher” modülü: seri port aç, protokolü konuş, image’ı yükle (host_flasher’ı çağırmak yerine doğrudan bu modül kullanılsın).

---

### 4. upload.py’yi yeni projeye göre toplama
- **Board ID:** Önce manuel (`--board-id`), sonra otomatik (GET_BOARD_ID). Otomatik mod: `--auto` veya board-id verilmezse cihaza sor.
- **Format:** Hem APJB hem ArduPilot-benzeri .apj (veya sadece image + board_id içeren JSON) okunabilsin.
- **Flasher:** Eski host_flasher yerine yeni protokolle konuşan bir modül (aynı repo içinde, örn. `flasher.py`).

---

## Kısa özet: Sırayla ne yapalım?

1. **Format:** upload.py’nin hem APJB hem ArduPilot .apj (veya basit JSON) okuyabilmesini sağla; `apj_analyze` ile test ettiğin dosya bu akışa girsin.
2. **Protokol taslağı:** GET_BOARD_ID + erase/write/verify komutlarını bir dokümanda (veya YOL_HARITASI’na) yaz; bootloader ve upload.py buna göre geliştirilsin.
3. **upload.py – board_id:** Önce `--board-id` ile çalışmaya devam et; ardından “cihaza sor” modunu ekle (seri port + GET_BOARD_ID).
4. **upload.py – flasher:** Eski host_flasher bağımlılığını kaldır; yeni protokolü konuşan flasher modülünü yaz ve upload.py’nin bunu kullanmasını sağla.
5. **Bootloader:** Yeni projede, sadece bu protokolü konuşan bootloader’ı implement et (ayrı repo/klasör).

İstersen bir sonraki adımda doğrudan “upload.py’ye ArduPilot .apj okuma + flasher’ı ayırma” ile başlayabiliriz; ya da önce protokol taslağını netleştiririz.
