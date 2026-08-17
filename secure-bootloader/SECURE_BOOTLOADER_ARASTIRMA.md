# Pixhawk Orange Cube+ için Güvenli Bootloader Araştırması (ArduPilot 4.3.0)

Bu doküman, **Pixhawk Orange Cube+** kartında sadece sizin `uploader.py` ile yüklenen firmware’lerin çalışmasını sağlamak için bootloader tarafında yapılabilecek düzenlemeleri ve alternatifleri özetler. Hedef sürüm: **ArduPilot 4.3.0**.

---

## 1. Kart ve Bootloader Bağlamı

- **Kart:** Pixhawk Orange Cube+ (Cube Orange+)
- **ArduPilot board adı:** `CubeOrangePlus`
- **MCU:** STM32H757 (STM32H7 ailesi)
- **Bootloader:** ArduPilot’un ChibiOS tabanlı bootloader’ı (`Tools/AP_Bootloader/`), PX4 protokolü ile uyumlu.
- **Bootloader donanım tanımı:** `libraries/AP_HAL_ChibiOS/hwdef/CubeOrange/hwdef-bl.dat` (Cube Orange ile aynı hwdef kullanılabilir; 4.3’te board adı `CubeOrangePlus` olarak geçer).

Orange Cube+ için bootloader, 32KB+ flash’a sahip H7 tabanlı kartlarda **secure boot** destekler (ArduPilot signing altyapısı bu kartları destekler).

---

## 2. İstediğiniz Davranış

- Sadece **sizin yazdığınız `uploader.py`** ile gelen firmware’lerin kabul edilmesi.
- Bootloader’ın bu kurala göre davranması.

Bunu sağlamanın iki ana yolu var: **(A) Firmware imzalama (signing)** ve **(B) Uploader kimlik doğrulama**.

---

## 3. Yöntem A: Firmware İmzalama (Signing) — Önerilen

ArduPilot’ta **secure boot** zaten var: bootloader’a bir veya daha fazla **public key** gömülür; sadece bu key’lerden biriyle **imzalanmış** firmware’ler açılışta kabul edilir. Bootloader “kim yükledi?”e bakmaz, “firmware imzası geçerli mi?”e bakar.

### Nasıl çalışır?

1. Siz bir **public/private key çifti** üretirsiniz (ArduPilot script’i Ed25519 benzeri bir yapı kullanır).
2. **Secure bootloader** bu public key(ler) ile derlenir ve karta yazılır.
3. Firmware’i **sadece sizin private key’inizle** imzalarsınız.
4. **uploader.py** bu imzalı `.apj` dosyasını karta yükler (normal yükleme gibi).
5. Bootloader açılışta firmware imzasını kontrol eder; sadece sizin public key’inize uyan imza varsa firmware’i çalıştırır.

Sonuç: Private key’i **sadece sizin `uploader.py`** (veya sizin kontrol ettiğiniz ortam) kullanırsa, pratikte sadece sizin ürettiğiniz imzalı firmware’ler çalışır. Bootloader’ı “sadece benim uploader’ımdan gelenleri kabul et” diye değiştirmenize gerek kalmaz; mevcut **signing** özelliği bu amacı karşılar.

### Adımlar (4.3.0 dalı için)

1. **ArduPilot 4.3.0’ı alın**
   ```bash
   git clone --depth 1 --branch ArduCopter-4.3 https://github.com/ArduPilot/ardupilot.git
   cd ardupilot
   git submodule update --init --recursive
   ```

2. **Key üretin**
   ```bash
   python3 -m pip install pymonocypher==3.1.3.2
   python3 Tools/scripts/signing/generate_keys.py VENDOR_ADI
   ```
   Çıkan dosyalar: `VENDOR_ADI_private_key.dat`, `VENDOR_ADI_public_key.dat`.  
   **Private key’i sadece uploader.py’nin kullandığı yerde tutun.**

3. **Secure bootloader derleyin (CubeOrangePlus)**
   ```bash
   python3 Tools/scripts/build_bootloaders.py CubeOrangePlus --signing-key=VENDOR_ADI_public_key.dat
   ```
   Bu, `Tools/bootloaders/CubeOrangePlus_bl.bin` dosyasını güncel secure bootloader ile değiştirir.

4. **İmzalı firmware derleyin**
   ```bash
   ./waf configure --board CubeOrangePlus --signed-fw
   ./waf copter   # veya plane, rover vb.
   python3 Tools/scripts/signing/make_secure_fw.py build/CubeOrangePlus/bin/arducopter.apj VENDOR_ADI_private_key.dat
   ```
   İsterseniz private key’i configure’a verip tek adımda imzalı build + upload da yapabilirsiniz:
   ```bash
   ./waf configure --board CubeOrangePlus --signed-fw --private-key VENDOR_ADI_private_key.dat
   ./waf copter --upload
   ```

5. **uploader.py’yi imzalı firmware ile kullanın**
   - uploader.py’nin yükleyeceği dosya her zaman **sizin private key ile imzalanmış** .apj olmalı.
   - İmzalama işlemini uploader.py içinde (veya öncesinde bir script ile) yapabilirsiniz; önemli olan private key’in sadece sizin script’inizde olması.

6. **Secure bootloader’ı karta yazma**
   - **Yöntem 1:** Önce imzalı firmware’i normal şekilde yükleyin (bir kez imzalı firmware’i yükleyebilmeniz gerekir; ilk kurulumda kartta hâlâ eski bootloader olabilir). Sonra MAVProxy’de `flashbootloader` veya GCS’te “Bootloader güncelle” ile firmware içinde gömülü olan secure bootloader’ı yazın.
   - **Yöntem 2:** DFU modunda (BOOT0 high ile açılış) `CubeOrangePlus_bl.bin`’i adres `0x08000000`’e yazın (STM32 Cube Programmer veya `dfu-util` ile).

Bu yöntemde bootloader kaynağında **ek bir “uploader tanıma” özelliği yazmanız gerekmez**; sadece ArduPilot’un mevcut signing altyapısını kullanırsınız.

---

## 4. Yöntem B: Bootloader’da “Sadece Bu Uploader” Kontrolü (Özel Geliştirme)

İsterseniz bootloader’ı **protokol seviyesinde** değiştirip “sadece belirli bir uploader’dan gelen paketleri kabul et” diyebilirsiniz. Bu, ArduPilot upstream’inde olmayan özel bir geliştirmedir.

### Olası tasarımlar

- **B1) Gizli anahtar (secret) ile kimlik doğrulama**  
  Bootloader, firmware yükleme oturumunun başında bir “secret” veya “token” bekler. Sadece sizin uploader.py bu secret’i biliyor ve ilk pakette gönderiyor; bootloader eşleşmezse yükleme başlamaz.  
  - Artı: Sadece sizin script’iniz yükleyebilir.  
  - Eksi: Secret bootloader binary’sinde sabit olacağı için çıkarılabilir; güvenlik “obscurity” seviyesinde kalır.

- **B2) Challenge–response**  
  Bootloader rastgele bir challenge üretir, uploader private key ile imzalar, bootloader public key ile doğrular. Bu, “uploader’ın sizin key’e sahip olduğunu” kanıtlar; firmware’i ayrıca imzalamaya gerek kalmadan “sadece bu uploader” kısıtı konulabilir (yine de firmware signing ile birlikte kullanmak daha güvenlidir).

- **B3) Uploader imzalı komutlar**  
  Yükleme komutları (ör. “şu adrese şu veriyi yaz”) uploader tarafından imzalanır, bootloader public key ile doğrular. Böylece bootloader sadece “doğru key ile imzalanmış” komutları işler.

B2/B3 için bootloader’da **AP_Bootloader** içinde protokol tarafına (ör. `PROTO_GET_DEVICE` sonrası bir “auth” adımı) yeni mesaj tipleri ve imza doğrulama kodu eklemeniz gerekir. Bu, ArduPilot 4.3.0 kodundan fork’layıp `Tools/AP_Bootloader/` altındaki C/C++ kodunu değiştirmeniz anlamına gelir.

**Özet:**  
- “Sadece benim uploader’ımdan gelen kod çalışsın” için **Yöntem A (signing)** yeterli ve resmî destekli.  
- “Uploader’ı da protokol seviyesinde tanısın” istiyorsanız **Yöntem B** özel geliştirme gerektirir; A ile birlikte kullanılabilir.

---

## 5. Bootloader Kaynak Kodu ve Derleme (4.3.0)

- **Kaynak:** `Tools/AP_Bootloader/` (ArduPilot repo).
- **Board config:** `libraries/AP_HAL_ChibiOS/hwdef/<BOARD>/hwdef-bl.dat`.  
  Cube Orange+ için board adı 4.3’te `CubeOrangePlus`; hwdef’ler genelde `CubeOrange` ile paylaşılır, `hwdef-bl.dat` da orada olabilir. Repo’da `CubeOrangePlus` veya `CubeOrange` klasörüne bakın.

**Sadece bootloader derleme (secure olmadan):**
```bash
./waf configure --board CubeOrangePlus --bootloader
./waf bootloader
```
Çıktı: `build/CubeOrangePlus/bin/` (veya `build/CubeOrangePlus/AP_Bootloader/` içinde .elf).  
Secure bootloader için yukarıdaki gibi `Tools/scripts/build_bootloaders.py` kullanın; bu script mevcut bootloader’ı signing key’lerle yeniden üretir.

**Bootloader’ı karta yükleme:**
- MAVLink: Çalışan firmware’den `flashbootloader` (MAVProxy) veya GCS “Bootloader Update”.
- DFU: BOOT0=1 ile açılış, ardından `CubeOrangePlus_bl.bin`’i 0x08000000’e yazma.

---

## 6. uploader.py ile Entegrasyon

- **Yöntem A kullanıyorsanız:**  
  uploader.py’nin yüklediği dosya **her zaman** sizin private key ile imzalanmış .apj olmalı. İmzalama işini:
  - ya build sonrası `make_secure_fw.py` ile yapıp çıkan .apj’i uploader’a verirsiniz,
  - ya da uploader.py içinde (private key’i güvenli şekilde kullanarak) aynı imzalama mantığını çağırabilirsiniz.  
  Bootloader ekstra “uploader tanıma” yapmaz; sadece firmware imzasına bakar.

- **Yöntem B ekliyorsanız:**  
  Bootloader’da yeni bir “auth” adımı tanımlayıp, uploader.py’nin bu adımda beklenen secret/challenge-response/imzayı göndermesini sağlamanız gerekir. Bu, hem bootloader hem uploader.py tarafında protokol değişikliği demektir.

---

## 7. Özet Tablo

| Amaç | Yöntem | Bootloader değişikliği | uploader.py |
|------|--------|------------------------|-------------|
| Sadece sizin imzalı firmware’ler çalışsın | A: Signing | Hayır (mevcut secure boot) | Private key ile .apj imzala, bu .apj’i yükle |
| Sadece sizin uploader yükleyebilsin (ek güvenlik) | B: Auth / challenge-response | Evet (özel kod) | Secret veya key ile bootloader’a kimlik doğrulama gönder |

**Pratik öneri:** Önce **Yöntem A**’yı kullanın: kendi key’inizi üretin, secure bootloader’ı derleyip yükleyin, firmware’i hep sizin private key ile imzalayın ve bu imzalı firmware’i sadece sizin uploader.py ile dağıtın/yükleyin. Bu, “sadece sizin ürettiğiniz kodların çalışması” için yeterli ve ArduPilot 4.3.0 ile uyumludur. İleride “uploader’ı da doğrula” isterseniz Yöntem B’yi ekleyebilirsiniz.

---

## 8. Referanslar

- ArduPilot Secure Firmware: https://ardupilot.org/dev/docs/secure-firmware.html  
- Signing script’leri ve README: `Tools/scripts/signing/` (ArduPilot repo, 4.3 dalında).  
- Bootloader README: `Tools/AP_Bootloader/README.md`  
- Bootloader güncelleme (kullanıcı): https://ardupilot.org/copter/docs/common-bootloader-update.html  
- DFU ile bootloader yükleme: https://ardupilot.org/dev/docs/using-DFU-to-load-bootloader.html  

Bu araştırma, önceki sohbetlerden bağımsız olarak hazırlanmıştır; doğrudan Orange Cube+, ArduPilot 4.3.0 ve sizin uploader.py kullanımınıza göre düzenlenmiştir.
