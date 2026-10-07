# Türkçe hızlı başlangıç

Python 3.10 veya daha yeni bir sürüm gereklidir. Komutları klonladığınız
deponun kök dizininde çalıştırın. Bu paket yerel olarak kurulur; PyPI'den
kurulum veya gerçek uçuş verisi indirme gerekmez.

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[charts]"
flight-delay --input examples/demo_flights.csv --output demo-output --min-flights 1 --min-route-flights 1 --charts
```

PowerShell etkinleştirme betiğini çalıştırmanıza izin vermiyorsa ortamı
etkinleştirmeden de kullanabilirsiniz:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[charts]"
.\.venv\Scripts\python.exe -m flight_delay --input examples/demo_flights.csv --output demo-output --min-flights 1 --min-route-flights 1 --charts
```

## macOS / Linux

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[charts]"
flight-delay --input examples/demo_flights.csv --output demo-output --min-flights 1 --min-route-flights 1 --charts
```

## Demo sonucunu kontrol etme

`examples/demo_flights.csv` **sentetik** bir örnektir; gerçek bir havayolunun
performansını göstermez. Sekiz satırdan bir iptal çıkarılır ve yedi uçuş
analiz edilir. Varsayılan eşikte `late rate` 3/7, yani yaklaşık %42,86'dır.
Tam 15 dakikalık gecikme geç sayılmaz: gecikmenin `--late-threshold`
değerinden **büyük** olması gerekir. Bunlar resmî BTS on-time istatistikleri
değildir. Veri sınırları için [demo notlarına](../examples/README.md) bakın.

`demo-output` içinde `summary.json`, aylık ölçümler, havalimanı/taşıyıcı
sıralamaları, riskli rotalar ve gecikme nedenlerinin paylarını içeren CSV
dosyaları oluşur. `--charts` ayrıca dört PNG grafik üretir. Yalnız CSV/JSON
istiyorsanız `python -m pip install .` ile kurun ve `--charts` eklemeyin.

## Kendi yerel CSV dosyanız

```sh
flight-delay --input "path/to/flights.csv" --output my-results --charts
```

Boşluk içeren yolları tırnak içine alın. Çıktı klasörü yeni veya boş
olmalıdır; yeniden çalıştırırken başka bir klasör seçin. Geçersiz girdide
komut hata mesajıyla birlikte 2 çıkış kodunu döndürür. Yazma hatası kısmi
dosyalar bırakabilir; bu durumda da yeni bir çıktı klasörü kullanın.

Gerekli CSV sütunları: `fl_date`, `dep_delay`, `origin`, `dest` ve
`op_unique_carrier`. Tarih için `YYYY-MM-DD` kullanın. `dep_delay` dakika
cinsindendir; negatif değer erken kalkış anlamına gelir. `cancelled=1`
olan satırlar ve eksik/geçersiz temel alanlar analize alınmaz.

- `--min-flights` varsayılanı 500'dür: havalimanı/taşıyıcı sıralaması için
  gereken en az analiz edilmiş uçuş sayısı.
- `--min-route-flights` varsayılanı 300'dür: rota sıralaması için eşik.
- `--late-threshold` varsayılanı 15 dakikadır.

Demoda kullanılan 1 uçuş eşikleri gerçek karşılaştırmalar için güvenilir
bir örneklem sağlamaz. Büyük CSV dosyaları belleğe tamamen yüklenir;
gerekirse önce uygun bir örneklem hazırlayın. Ayrıntılı sütun, metrik ve
çıktı tanımları [README](../README.md) içindedir.
