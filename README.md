# Mekensis Havuz Isıl Yük Hesabı

Mekensis Mühendislik tarafından geliştirilen, yüzme havuzlarının ısıtma kapasitesini hesaplayan ve yazdırılabilir rapor üreten bir hesap programıdır. Açık ve kapalı havuzlar için ayrı hesap modları bulunur.

- **Açık havuz:** Türkiye'nin 81 ili için aylık iklim verileri kullanılarak işletme sezonu boyunca her ayın gece ısı kaybı, gündüz güneş kazancı ve su kütlesinin ısıl tamponu hesaplanır; sezon içindeki en yüksek ısıtma ihtiyacı dizayn gücü olarak raporlanır.
- **Kapalı havuz:** Mahal şartlarına göre sürekli işletme (rejim) yükü ile havuzun ilk dolumdan hedef sıcaklığa ısıtılması (ilk ısıtma) için gereken kapasite hesaplanır.

## Çalıştırma

Program, harici kütüphane veya sunucu gerektirmeyen tek bir HTML dosyasıdır (`Mekensis_Havuz_Isil_Yuk_Analizi.html`).

1. Dosya indirilir.
2. Güncel bir tarayıcıda (Chrome, Edge, Firefox, Safari) çift tıklanarak açılır.
3. Girdiler değiştirildikçe sonuçlar anında güncellenir.
4. Rapor, sayfa altındaki **"Raporu Yazdır / PDF Kaydet"** düğmesiyle yazdırılabilir veya PDF olarak kaydedilebilir.

İnternet bağlantısı gerekmez; tüm iklim verileri dosyanın içindedir.

## Girdiler

**Ortak (havuz geometrisi)**

| Girdi | Birim |
|---|---|
| Havuz konumu (açık / kapalı) | – |
| Su yüzey alanı | m² |
| Ortalama derinlik | m |
| Hedef su sıcaklığı | °C |
| Taze su tamamlama debisi | lt/sn |
| Kullanım şekli (rapor açıklaması) | – |

**Açık havuz**

| Girdi | Birim |
|---|---|
| İl (81 il, aylık iklim veritabanı) | – |
| Saha / havuz rakımı | m |
| Sezon başlangıç ve bitiş ayı | – |
| Detaylı incelenen referans ayı | – |
| Referans ay için gündüz/gece dış sıcaklık, günlük güneş ışınımı, rüzgar hızı, bağıl nem (il verisinden gelir, elle değiştirilebilir) | °C, kWh/m²·gün, m/s, % |
| Çevre rüzgar koruması / kapalılık oranı | % |
| Gece izin verilen su soğuması | °C |
| Güneş radyasyonu etkinliği (açık / parçalı / kapalı / sıfır) | – |
| Gece havuz örtüsü (var / yok) | – |

**Kapalı havuz**

| Girdi | Birim |
|---|---|
| Mahal hava sıcaklığı | °C |
| Mahal bağıl nemi | % |
| Su yüzeyindeki hava hızı | m/s |
| Doldurma / şebeke suyu sıcaklığı | °C |
| İlk ısıtma süresi | saat |

## Çıktılar

**Açık havuz**

- Klasik teorik pik yük (güneşsiz, rüzgar korumasız gece kaybı) — kW ve kcal/h
- Önerilen sistem dizayn gücü — kW ve kcal/h
- Referans ay için güneş kazancı, ısıl tampon, günlük buharlaşan su miktarı (kg/gün) ve havuz devresi debisi (m³/h, ΔT = 5 °C)
- Sezon boyunca aylık ısı dengesi tablosu ve grafiği (pik ay işaretli)
- Referans ay için gündüz/gece kayıp ve kazanç dökümü (buharlaşma, rüzgarla taşınım, açık gökyüzüne ışınım, taban/duvar iletimi, taze su, güneş, ısıl tampon)

**Kapalı havuz**

- Sürekli işletme (rejim) kapasitesi — kW ve kcal/h
- İlk ısıtma kapasitesi — kW ve kcal/h
- Buharlaşan su miktarı (nem alma yükü, kg/h ve kg/gün), gizli ve duyulur ısı kaybı, havuz devresi debisi
- 24 / 48 / 72 / 96 saat ve seçilen süre için ilk ısıtma güç karşılaştırma tablosu ve grafiği
- Kayıp kalemlerinin kW, kcal/h ve yüzde dağılımı

## İklim verisi

81 ilin her biri için ayrı aylık veri bulunur. Veriler `tools/iklim_verisi_guncelle.py` betiğiyle kaynaklardan çekilir ve HTML dosyasındaki `CITIES` tablosuna yazılır; tablo elle düzenlenmez.

| Değer | Kaynak |
|---|---|
| İstasyon konumu ve rakımı (`refAlt`) | MGM il merkez istasyonu (servis.mgm.gov.tr). MGM kaydında rakımı 0 görünen Kahramanmaraş, Kocaeli, Rize ve Sinop için PVGIS'in arazi modeli (DEM) rakımı kullanılır. |
| Gündüz / gece dış sıcaklığı | MGM İllere Ait Mevsim Normalleri (1991-2020): ortalama en yüksek / ortalama en düşük sıcaklık. İstanbul için normal tablosu yayımlanmadığından MGM genel istatistik verisi (1950-2025) kullanılır. |
| Güneş ışınımı | PVGIS 5.3, PVGIS-SARAH3 uydu verisi (2005-2023), yatay düzlem günlük ortalama ışınımı (kWh/m²·gün). |
| Rüzgar (10 m) ve bağıl nem | PVGIS 5.3 tipik meteorolojik yıl (TMY, ERA5 yeniden analiz verisi, 2005-2023), aylık ortalama. İstanbul ve Tekirdağ'ın TMY verisindeki bozuk Aralık bölümleri dışarıda bırakılır. |

Gündüz ve gece süreleri sabit değildir; her ay için ilin enlemine göre astronomik gün uzunluğu hesaplanır (Cooper deklinasyon bağıntısı, Klein temsili günleri). Güneş kazancı, günlük ışınımın gündüz süresine yayılmasıyla bulunur.

İl seçildiğinde saha rakımı ilin istasyon rakımına getirilir. Farklı bir rakım girildiğinde sıcaklıklar 0,65 °C/100 m ile düzeltilir.

Rüzgar ve nem, istasyon ölçümü değil ~25 km çözünürlüklü yeniden analiz (ERA5) verisidir. Özellikle kıyı illerinde istasyon değerlerinden sapabilir. Kesin değer gereken projelerde referans ay girdileri, MGM istasyon verisiyle elle düzeltilmelidir.

Verilerin yeniden üretilmesi:

```
python3 tools/iklim_verisi_guncelle.py --cache <önbellek klasörü>
```

## Not

Hesap yöntemleri ve kabuller henüz bağımsız bir doğrulamadan geçmemiştir. Sonuçlar, proje kararlarında mühendislik değerlendirmesiyle birlikte kullanılmalıdır.
