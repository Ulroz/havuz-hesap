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
| Referans ay için gündüz/gece dış sıcaklık, güneş ışınımı, rüzgar hızı, bağıl nem (il verisinden gelir, elle değiştirilebilir) | °C, W/m², m/s, % |
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
- Referans ay için gündüz/gece kayıp ve kazanç dökümü (buharlaşma, taşınım + ışınım, taban/duvar iletimi, taze su, güneş, ısıl tampon)

**Kapalı havuz**

- Sürekli işletme (rejim) kapasitesi — kW ve kcal/h
- İlk ısıtma kapasitesi — kW ve kcal/h
- Buharlaşan su miktarı (nem alma yükü, kg/h ve kg/gün), gizli ve duyulur ısı kaybı, havuz devresi debisi
- 24 / 48 / 72 / 96 saat ve seçilen süre için ilk ısıtma güç karşılaştırma tablosu ve grafiği
- Kayıp kalemlerinin kW, kcal/h ve yüzde dağılımı

## Not

Hesap yöntemleri ve kabuller henüz bağımsız bir doğrulamadan geçmemiştir. Sonuçlar, proje kararlarında mühendislik değerlendirmesiyle birlikte kullanılmalıdır.
