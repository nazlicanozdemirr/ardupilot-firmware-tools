# İki Yaklaşımın Karşılaştırması: Wrapper Planı vs Mevcut (Binary Bundle) Plan

## Özet

**Verdiğin plan (wrapper + APJPKG kapsayıcı) bu proje için daha sağlıklı ve doğru yön.** Aşağıda nedenleri, farklar ve tek taraflı öneriler netleştirildi.

---

## 1. Temel fark: Ne değiştiriyoruz?

| | Wrapper planı | Benim kurduğum (binary bundle) |
|--|----------------|----------------------------------|
| **Standart .apj** | Değişmiyor. Her kart için normal .apj üretilmeye devam eder. | Kullanılmıyor; yerine ham .bin/.hex alınıp binary kapsayıcıya konuyor. |
| **image alanı** | Olduğu gibi taşınır: zlib+base64. Encode/decode’a dokunulmaz. | Ham binary saklanıyor; ArduPilot .apj ile uyum yok. |
| **Yükleme** | Mevcut uploader çağrılır (tek .apj bekler). Wrapper sadece “hangi .apj”i vereceğini seçer. | Ya eski host_flasher (farklı protokol) ya da yeni yazılacak flasher. |
| **Risk** | Düşük: flash protokolü, doğrulama, external flash akışı mevcut uploader’da kalır. | Yüksek: protokolü yeniden yazmak veya başka bir flasher’a bağlamak gerekir. |

**Sonuç:** Wrapper planı “en az şeyi değiştirir”; benimki standart .apj’den kopuk, özel bir dünya kurar.

---

## 2. image = zlib + base64

ArduPilot .apj’de `image` alanı şöyle:

- **Ham binary** → zlib ile sıkıştırılır → base64 ile kodlanır → JSON’da `"image": "eNq8vA..."` olur.
- `image_size` = zlib decompress sonrası boyut (bytes).

Örnek dosyada doğrulandı:

- `base64.b64decode(image)` → 1.128.446 byte (sıkıştırılmış).
- `zlib.decompress(...)` → 1.647.512 byte = `image_size`.

**Wrapper planında:** Bu veriyi **hiç decode etmiyorsun**. İç kaydı olduğu gibi kapsayıcıya koyuyorsun; geçici .apj’yi mevcut uploader’a veriyorsun; decode’u uploader yapıyor. **Doğru ve güvenli.**

**Benim planda:** Binary kapsayıcıda ham binary saklıyordum; zlib/base64 hiç yoktu. ArduPilot tool zinciriyle uyum için ek iş (decode/encode) gerekir; hata riski artar.

---

## 3. Kapsayıcı formatı

| | Wrapper planı (APJPKGv1) | Benimki (APJB binary) |
|--|---------------------------|------------------------|
| **Format** | JSON. `magic`, `format_version`, `description`, `version`, `firmwares` (board_id → tam .apj kaydı). | Binary. Magic "APJB", versiyon, sayı, sonra board_id+size+raw_data. |
| **İçerik** | Her board_id için **tam** standart .apj kaydı: board_id, image, image_size, board_revision, extf_image, extf_image_size, summary, version, … | Sadece board_id + ham binary image. Metadata yok. |
| **extf_image** | Korunur (iç kayıtta olduğu gibi). | Yok. |
| **Uploader beklentisi** | Tek standart .apj dosyası; mevcut uploader değişmez. | Standart .apj değil; özel flasher veya geçici .apj üretmek gerekir. |

**Sonuç:** APJPKGv1, standart .apj dünyasına birebir oturuyor; metadata ve external flash desteği kaybolmuyor.

---

## 4. Sorumluluk ayrımı

**Wrapper planı:**

- **Packer:** Normal .apj’leri oku → board_id çıkar → aynı kaydı kapsayıcıya ekle (image’a dokunma).
- **Wrapper uploader:** Port aç → board_id oku → kapsayıcıdan ilgili kaydı seç → geçici .apj yaz → mevcut uploader’ı çağır.
- **Mevcut uploader:** Erase, program, verify, gerekirse external flash; tek .apj ile çalışmaya devam eder.

**Benimki:**

- Packer: .bin/.hex → ham binary → binary kapsayıcı.
- upload.py: board_id (şu an manuel), bundle’dan binary çıkar, geçici .bin yaz, **başka bir flasher** (örn. eski host_flasher) çağır. O flasher ArduPilot .apj formatını bilmiyor; uyum için ya yeni bir “.apj üretici” ya da tamamen farklı protokol gerekir.

**Sonuç:** Wrapper planı tek sorumluluk: “doğru firmware’i seç”; flash işi kanıtlanmış uploader’da. Benimki ya ArduPilot uploader’ı bypass ediyor ya da ona uyum için ek katman gerektiriyor.

---

## 5. Benim planla farklar (maddeler halinde)

1. **Standart .apj’yi bozmamak**  
   Wrapper: Build hattı aynı; çıktı yine tek kart = tek .apj. Kapsayıcı sadece bunları bir araya getirir.  
   Benimki: Tek kart çıktısı olarak .apj kullanılmıyor; binary bundle farklı bir format.

2. **image’ı yeniden encode etmemek**  
   Wrapper: image zlib+base64 olarak taşınır; packer/wrapper decode etmez.  
   Benimki: Ham binary; ArduPilot tarafındaki zlib+base64 ile uyum için decode/encode gerekir.

3. **Mevcut uploader’ı kullanmak**  
   Wrapper: Geçici standart .apj → mevcut uploader. Protokol ve doğrulama aynen kalır.  
   Benimki: Farklı bir flasher (veya yeni protokol); ArduPilot ekosistemiyle doğal uyum yok.

4. **Metadata bütünlüğü**  
   Wrapper: board_revision, extf_image, summary, version vb. iç kayıtta durur; uploader ne bekliyorsa o.  
   Benimki: Sadece image; diğer alanlar yok.

5. **Board ID kaynağı**  
   İkisinde de cihazdan okunabilir; wrapper planında “bootloader ile sync → board_id oku” net tanımlı. Benimki de aynı fikri kullanabilir ama kapsayıcı ve uploader tarafı farklı.

---

## 6. Hangi yol daha iyi?

**Bu proje için (ArduPilot uyumlu kartlar, mevcut uploader’ın kullanılması hedefleniyorsa):**

- **Wrapper + APJPKGv1 planı daha iyi.**  
  Sebepler:
  - Standart .apj ve ArduPilot dokümantasyonuyla uyumlu.
  - Flash protokolünü ve doğrulamayı yeniden yazmıyorsun; mevcut uploader’a güveniyorsun.
  - image = zlib+base64’e dokunmuyorsun; hata riski az.
  - extf_image ve tüm metadata korunuyor.
  - Kart envanteri, board_id tablosu, build süreci net tanımlanmış; test ve hata senaryoları plana uygun.

**Binary bundle (benimki) ne zaman mantıklı?**

- ArduPilot dünyasına hiç girmeyeceksen, kendi bootloader’ın ve kendi flasher’ın varsa, “tek binary blob” yeterliyse. O zaman standart .apj’ye uyum zorunlu değildir. Şu anki hedef “standart .apj + mevcut uploader” ise binary bundle gereksiz karmaşıklık ve uyumsuzluk getirir.

---

## 7. Wrapper planına eklenebilecek küçük notlar

- **Hangi uploader?** Wrapper’ın çağıracağı program net olmalı (örn. `python -m pymavlink.tools.uploader` veya ArduPilot repo’daki belirli script). Komut satırı: `uploader_script.py --port ... temp.apj` gibi.
- **Geçici .apj yolu:** Windows’ta geçici dizin, yetki ve yol uzunluğu sorun çıkarmamalı; mümkünse kısa bir isimle (örn. `board_140.apj`) yazılabilir.
- **Packer’da opsiyonel doğrulama:** İç .apj’deki `image` için `len(zlib.decompress(base64.b64decode(image))) == image_size` kontrolü yapılabilir; duplicate board_id ile birlikte bu da “fail” kriteri olabilir.
- **apj_analyze.py:** `--save-image` kullanıyorsa gerçek ham binary için `zlib.decompress(base64.b64decode(image))` kullanılmalı; şu an sadece base64 decode var, bu yanlış (sıkıştırılmış çıktı verir).

---

## 8. Sonuç ve tavsiye

- **Planı uygula:** Kapsayıcı = APJPKGv1 JSON; içte her board_id için tam standart .apj kaydı; packer image’a dokunmasın; wrapper board_id okuyup geçici .apj üretsin ve mevcut uploader’ı çağırsın.
- **Mevcut binary bundle (APJB, build_bundle.py, apj_bundle.py):** ArduPilot odaklı ilk sürümde kullanılmasın; istersen ileride “alternatif format” olarak tutulabilir veya kaldırılabilir.
- **YOL_HARITASI.md:** Wrapper planına göre güncellenebilir (adımlar: kart listesi → packer → wrapper → test → dağıtım).

Bu analiz, verdiğin planın daha sağlıklı ve bu proje için doğru seçim olduğunu ve neden öyle olduğunu açıklıyor; uygulama sırası ve hata senaryoları da planla uyumlu.
