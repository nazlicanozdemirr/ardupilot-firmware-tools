# APJ Evrensel Firmware Projesi – Genel Kullanım Kılavuzu

Bu dokümantasyon, **tek bir firmware paketi** ile **birden fazla uçuş kartı** (CubeOrangePlus, Pixhawk 6X vb.) için doğru yazılımı seçip yükleyen sistemin nasıl kullanılacağını açıklar.

---

## 1. Proje Ne Yapıyor?

- **Amaç:** Farklı kart tipleri için ayrı ayrı `.apj` dosyası taşımak yerine, **tek bir “evrensel” paket** (universal_firmware_4.7.0.apj) kullanmak. Kartı taktığınızda sistem **kartın tipini otomatik algılar**, paketin içinden **o karta uygun firmware’i seçer** ve yükler.
- **Akış özeti:**
  1. Build aşamasında her kart için standart ArduPilot `.apj` üretilir.
  2. Bu `.apj` dosyaları **tek bir kapsayıcı dosyada** (APJPKGv1 formatında) birleştirilir.
  3. Yükleme sırasında bağlı kartın **board_id**’si (uploader `--identify` ile) okunur.
  4. Kapsayıcıdan ilgili **board_id**’ye ait tek-kart `.apj` kaydı seçilir.
  5. Seçilen kayıt geçici bir `.apj` dosyasına yazılır ve **mevcut ArduPilot uploader** bu dosyayla normal yükleme (erase / program / verify) yapar.

Böylece tek komutla, hangi kart takılı olursa olsun doğru firmware yüklenir; flash protokolü ve doğrulama mevcut uploader’da kaldığı için risk azalır.

---

## 2. Dosyalar ve Görevleri

| Dosya | Görevi | Kim Kullanır |
|-------|--------|---------------|
| **create_fat_apj.py** | Birden fazla tek-kart `.apj` dosyasını alıp **tek APJPKGv1 kapsayıcı** (universal_firmware_*.apj) üretir. İçerik (image, metadata) olduğu gibi taşınır; yeniden encode edilmez. | Geliştirici / build sorumlusu (yeni sürüm veya yeni kart eklendiğinde). |
| **smart_upload.py** | Kapsayıcı dosyayı açar, bağlı kartın **board_id**’sini (uploader `--identify` ile) okur, ilgili iç `.apj` kaydını seçer, geçici `.apj` oluşturur ve **uploader.py**’ı bu dosyayla çalıştırır. | Saha / operatör: yükleme yaparken tek komutla kullanılır. |
| **apj_analyze.py** | Tek bir ArduPilot `.apj` dosyasını (JSON) açar; **board_id**, **magic**, **description**, **image_size**, **summary** vb. alanları listeler. İsteğe bağlı olarak `image` alanını (zlib+base64 decode) binary dosyaya kaydeder. | Geliştirici: yeni `.apj` eklerken board_id kontrolü veya debug için. |
| **entegre_edilecek_uploader.py** | Kendi uploader kodunuza **entegre etmek** için kullanacağınız **minimal kod parçası**dır. İçinde `_is_fat_package()`, `select_firmware_from_fat_package()` ve main’e eklenecek örnek blok bulunur. Projeyi tek başına çalıştırmaz; sadece kopyala-yapıştır kaynağı. | Geliştirici: kendi uploader projesine fat-APJ desteği eklerken. |
| **uploader.py** | ArduPilot’un standart seri firmware yükleyicisi (bu projede dışarıda tutulur; örn. `.apj_proje_dosyaları` içinde). `--port`, firmware `.apj` yolu, `--identify`, `--verify-firmware-is` vb. destekler. | Hem **smart_upload.py** hem de doğrudan tek `.apj` yüklerken kullanılır. |

**Not:** Gerçek flash işlemi (erase, program, verify) her zaman **uploader.py** tarafından yapılır; **smart_upload** ve **entegre parça** sadece “hangi .apj dosyasını vereceğini” seçer.

---

## 3. Genel Kullanım Akışı

### A) Paket oluşturma (yeni sürüm veya yeni kart)

1. Her kart için standart ArduPilot build’inden tek-kart `.apj` dosyalarını elde edin (örn. `arduplane.apj`, `arduplane (1).apj`).
2. **create_fat_apj.py** ile bunları tek kapsayıcıda birleştirin:

   ```powershell
   python create_fat_apj.py -o "C:\...\universal_firmware_4.7.0.apj" ^
       "C:\...\arduplane.apj" ^
       "C:\...\arduplane (1).apj"
   ```

3. Çıktıda her `.apj` için `board_id` ve `summary` satırlarını görürsünüz; son satırda kapsayıcı yolu ve firmware sayısı yazar.
4. Oluşan **universal_firmware_4.7.0.apj** dosyasını dağıtım için sabit bir klasörde (örn. `.apj_proje_dosyaları`) tutun.

### B) Karta firmware yükleme (operatör)

1. Kartı USB ile bilgisayara bağlayın; gerekirse bootloader moduna alın (çoğu kartta USB’yi çıkarıp tekrar takmak yeterlidir).
2. Cihazın bağlı olduğu COM portunu bilin (örn. COM12, COM15).
3. **smart_upload.py**’ı tek komutla çalıştırın:

   ```powershell
   python smart_upload.py --port COM12 "C:\...\universal_firmware_4.7.0.apj"
   ```

4. Script sırasıyla:
   - `uploader.py --identify` çalıştırarak board_id’yi okur,
   - Kapsayıcıdan ilgili firmware’i seçer,
   - Geçici `.apj` oluşturur,
   - `uploader.py`’ı bu dosyayla çağırır.
5. Konsolda **Erase / Program / Verify: 100%** ve **Yukleme basarili.** mesajlarını görmelisiniz.

### C) Yüklemenin doğru olduğunu kontrol etme

Kartta beklediğiniz tek-kart `.apj`’nin yüklü olup olmadığını, **flash’a yazmadan** kontrol etmek için:

```powershell
python "C:\...\uploader.py" --port COM12 --verify-firmware-is "C:\...\arduplane.apj"
```

- **Verify: 100%** ve hata yoksa, kartta o `.apj` ile birebir aynı firmware vardır.
- CubeOrangePlus için kendi `.apj`, Pixhawk 6X için kendi `.apj` yolu kullanılmalıdır.

---

## 4. Hangi Dosyayı Ne Zaman Kullanacağım?

| Durum | Kullanılacak dosya / komut |
|-------|----------------------------|
| Yeni sürüm çıktı, tüm kartlar için paketi yeniden üretmek | **create_fat_apj.py** (tüm güncel tek-kart .apj’leri argüman olarak verin). |
| Sahada karta firmware yüklemek (tek komut) | **smart_upload.py** + port + universal_firmware_*.apj yolu. |
| Kartta hangi firmware yüklü kontrol etmek (yazmadan) | **uploader.py** + `--verify-firmware-is` + ilgili tek-kart .apj yolu. |
| Yeni bir kart tipi eklemek | Önce **apj_analyze.py** ile yeni .apj’deki board_id’yi not alın; sonra **create_fat_apj.py**’e bu .apj’yi de ekleyip paketi yeniden oluşturun. |
| Kendi uploader yazılımıma bu mantığı entegre etmek | **entegre_edilecek_uploader.py** içindeki fonksiyonları ve main örneğini kendi projenize kopyalayıp uyarlayın. |

---

## 5. Örnek Kartlar ve board_id (Referans)

Bu projede kullanılan örnek değerler (kendi build’inize göre değişebilir):

- **CubeOrangePlus** – board_id: **1063** (tek .apj: örn. `arduplane.apj`)
- **Pixhawk 6X** – board_id: **53** (tek .apj: örn. `arduplane (1).apj`)

Kapsayıcı içinde `firmwares["1063"]` ve `firmwares["53"]` olarak saklanır; **smart_upload** karttan okunan board_id’ye göre doğru olanı seçer.

---

## 6. Sık Karşılaşılan Hatalar ve Anlamları

| Mesaj / Durum | Olası neden | Ne yapılır? |
|---------------|-------------|-------------|
| Kapsayici dosya bulunamadi | Verilen .apj yolu yanlış veya dosya taşınmış. | Tam yolu kontrol edin; gerekirse tek tırnak içinde verin. |
| Board ID otomatik okunamadi / timeout | Kart bootloader modunda değil veya başka yazılım portu kullanıyor. | USB’yi çıkarıp takın; Mission Planner vb. kapatın; doğru COM portunu kullanın. |
| Kapsayici icinde board_id=... icin firmware yok | Kullanılan pakette bu board_id için kayıt yok. | Bu kart için .apj’yi **create_fat_apj.py** ile pakete ekleyip yeni universal_*.apj üretin. |
| Ayni board_id icin birden fazla .apj var | create_fat_apj’ye verilen iki .apj aynı board_id’ye sahip. | Build ayarlarını veya listeyi düzeltin; her board_id pakette tek olmalı. |
| magic != 'APJFWv1' | Dosya standart ArduPilot .apj değil (veya bozuk). | Sadece build çıktısı tek-kart .apj dosyalarını kullanın. |

---

## 7. Kısa Özet

- **create_fat_apj.py** → Tek kapsayıcı (universal_*.apj) **üretmek** için.
- **smart_upload.py** → Bu kapsayıcıyı kullanarak **karta otomatik seçimle yükleme** yapmak için.
- **apj_analyze.py** → Tek .apj **incelemek** veya board_id **kontrol etmek** için.
- **entegre_edilecek_uploader.py** → Kendi uploader’ınıza **entegre edeceğiniz minimal kod** için.
- **uploader.py** → Gerçek yükleme ve doğrulama (**--verify-firmware-is**) için; proje bu aracı değiştirmez, sadece “hangi .apj?” sorusunu çözer.

Bu kılavuz, projeyi dokümantasyon olarak sunarken “neyi, hangi dosyayı, nasıl kullanacağım?” sorusuna yanıt vermek üzere hazırlanmıştır.
