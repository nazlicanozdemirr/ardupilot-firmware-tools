# ArduPilot Firmware Tools

Bu depo, staj döneminde geliştirilen ArduPilot APJ paketleme, firmware yükleme,
özel bootloader ve kart tanımı çalışmalarını düzenli bir arşiv altında toplar.

## İçerik

- `tools/apj-bundle/`: APJ inceleme, paketleme ve yükleme yardımcıları.
- `tools/integration/`: firmware paketleme/yükleme entegrasyon denemeleri.
- `secure-bootloader/`: anahtar üretimi ve güvenli bootloader araştırmaları.
- `hwdef/`: kart ve bootloader pin/port tanımı örnekleri.
- `romfs/`: ROMFS başlıkları ve önceki çalışma kopyaları.
- `reference/`: ArduPilot kaynak kodu üzerinde yapılan deneysel değişiklikler.
- `firmware-samples/`: testlerde kullanılan derlenmiş APJ/HEX örnekleri.
- `docs/`: çalışma notları ve donanım tabloları.

## Python ortamı

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Araçların kabul ettiği parametreleri görmek için ilgili betiği `--help` ile
çalıştırın. Örneğin:

```powershell
python .\tools\apj-bundle\apj_analyze.py --help
```

## Güvenlik notu

`generate_keys.py` gerçek bir özel anahtar oluşturabilir. Üretilen anahtarlar
Git tarafından yok sayılır; özel anahtarları hiçbir zaman depoya eklemeyin.

`firmware-samples/` altındaki dosyalar kaynak kod yerine test girdisi ve arşiv
niteliğindedir. Donanıma yüklemeden önce hedef kartı ve bootloader uyumluluğunu
ayrıca doğrulayın.

ArduPilot'tan türetilmiş veya ArduPilot ile birlikte kullanılan dosyalar kendi
upstream lisans koşullarına tabidir.
