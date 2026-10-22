#!/usr/bin/env node
// Açık havuz ısı kaybı modelinin saha ölçümüyle doğrulanması (gece enerji dengesi).
//
// Saha: Tekirova (Antalya) sahilinde, denize sıfır bir otelin açık havuzu.
// 2000 m² su yüzeyi, ortalama 1,5 m derinlik (3000 m³), örtü yok, havuz kullanılmıyor.
// Isıtma: su kaynaklı ısı pompası, sabit 600 kW kabul edilir.
// Ölçülen kayıp = 600 kW − (havuz suyunun ısıl kapasitesi × sıcaklık değişimi / süre).
//
// Hava verisi: Open-Meteo arşiv API'si (ERA5 tabanlı yeniden analiz, CC BY 4.0), ızgara noktası
// 36,52 K / 30,47 D, saatlik, yerel saat. Işınım değeri önceki saatin ortalamasıdır.
// Tesiste rüzgâr ölçümü yoktur; sonuç kullanılan rüzgâr kaynağına duyarlıdır.
//
// Hesap fonksiyonları ve sabitler index.html'den okunur; böylece program değiştikçe test de onu ölçer.
// Çevre koruması uygulanmaz (k = 1): rüzgâr yalnızca 10 m'den 0,3 m'ye indirilir.
//
// Kullanım: node tools/dogrulama/acik_havuz_gece_dengesi.js

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// index.html içinden adı verilen fonksiyonları (süslü parantez eşleştirerek) ve sabitleri çıkarır
function extractFunction(name) {
  const start = html.indexOf(`function ${name}(`);
  if (start < 0) throw new Error(`index.html içinde fonksiyon bulunamadı: ${name}`);
  let i = html.indexOf('{', start), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) break;
  }
  return html.slice(start, i + 1);
}
function extractConst(name) {
  const m = html.match(new RegExp(`const ${name} = [^\\n]*;`));
  if (!m) throw new Error(`index.html içinde sabit bulunamadı: ${name}`);
  return m[0];
}

const CONSTS = ['CITIES', 'LATENT_HEAT', 'WATER_EMISSIVITY', 'STEFAN_BOLTZMANN',
  'WIND_Z0_WATER', 'WIND_HEIGHT_FACTOR', 'ATM_PRESSURE_PA'];
const FUNCS = ['getSatVaporPressure', 'getVaporPressureAt', 'getDewPointFromVapor', 'getSkyTemp',
  'evapKwToKgPerHour', 'getMakeupHeatKw', 'getMoistAirDensity', 'getHumidityRatio',
  'getOutdoorEvapHeatKw', 'getOutdoorConvKw', 'getSkyRadiationKw'];
const ctx = {};
vm.createContext(ctx);
vm.runInContext([...CONSTS.map(extractConst), ...FUNCS.map(extractFunction),
  `this.m = { ${[...CONSTS, ...FUNCS].join(', ')} };`].join('\n'), ctx);
const M = ctx.m;

// Saatlik hava verisi
const rows = fs.readFileSync(path.join(__dirname, 'open_meteo_tekirova_2025-04.csv'), 'utf8')
  .trim().split('\n').slice(1).map(l => l.split(','));
const wx = new Map(rows.map(([t, T, Td, V, G]) => [t, { T: +T, Td: +Td, V: +V, G: +G }]));
const key = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ` +
  `${String(d.getHours()).padStart(2, '0')}:00`;
function weatherAt(d) {
  const t0 = new Date(d); t0.setMinutes(0, 0, 0);
  const t1 = new Date(t0.getTime() + 3600e3);
  const a = wx.get(key(t0)), b = wx.get(key(t1));
  if (!a || !b) throw new Error(`Hava verisi eksik: ${key(t0)}`);
  const f = (d - t0) / 3600e3;
  const lerp = k => a[k] * (1 - f) + b[k] * f;
  return { T: lerp('T'), Td: lerp('Td'), V: lerp('V'), G: b.G };   // G: [t0, t1] aralığının ortalaması
}

// Havuz ve saha kabulleri
const AREA = 2000, DEPTH = 1.5, VOLUME = 3000, HEAT_PUMP_KW = 600;
const CAP_KWH_PER_K = VOLUME * 1000 * 4.186 / 3600;
const city = M.CITIES.antalya;
const tGround = city.months.reduce((s, mo) => s + (mo.tDay + mo.tNight) / 2.0, 0) / 12.0;   // programdaki gibi
const aWet = AREA + 4.0 * Math.sqrt(AREA) * DEPTH;

// Gece aralıkları: başlangıç/bitiş ve ölçülen su sıcaklığı (yüzey ve dip ortalaması, °C)
const NIGHTS = [
  { name: '20→21 Nisan 2025', t0: '2025-04-20T21:30', t1: '2025-04-21T08:00', w0: 28.1, w1: 27.5 },
  { name: '21→22 Nisan 2025', t0: '2025-04-21T18:00', t1: '2025-04-22T07:30', w0: 29.95, w1: 28.85 },
];
const READING_ERROR_K = 0.3;   // tek termometre okuma belirsizliği

let fail = false;
for (const n of NIGHTS) {
  const t0 = new Date(n.t0), t1 = new Date(n.t1);
  const hours = (t1 - t0) / 3600e3, steps = Math.round(hours / 0.1), dt = hours / steps;
  let loss = 0, solar = 0;
  for (let i = 0; i < steps; i++) {
    const t = new Date(t0.getTime() + (i + 0.5) * dt * 3600e3);
    const tw = n.w0 + (n.w1 - n.w0) * (i + 0.5) / steps;
    const w = weatherAt(t);
    const pVapor = M.getSatVaporPressure(w.Td);
    const u = w.V * M.WIND_HEIGHT_FACTOR;
    const evap = M.getOutdoorEvapHeatKw(AREA, tw, w.T, pVapor, u);
    const q = evap + M.getMakeupHeatKw(evap, 0, tw, tGround) + M.getOutdoorConvKw(AREA, u, tw, w.T) +
      M.getSkyRadiationKw(AREA, tw, w.T, pVapor) + 0.85 * aWet * Math.max(0, tw - tGround) / 1000.0;
    loss += q * dt;
    solar += AREA * w.G * 0.85 / 1000.0 * dt;   // programdaki güneş soğurma oranı
  }
  const modelNet = (loss - solar) / hours;
  const measured = HEAT_PUMP_KW - (n.w1 - n.w0) * CAP_KWH_PER_K / hours;
  const tol = READING_ERROR_K * CAP_KWH_PER_K / hours;
  const ok = Math.abs(modelNet - measured) <= tol;
  if (!ok) fail = true;
  console.log(`${n.name} (${hours.toFixed(1)} sa): ölçülen ${measured.toFixed(0)} ± ${tol.toFixed(0)} kW, ` +
    `model ${modelNet.toFixed(0)} kW (${((modelNet / measured - 1) * 100).toFixed(0)}%)  ${ok ? 'UYGUN' : 'SAPMA'}`);
}
console.log(`Rüzgâr yükseklik çarpanı (10 m → 0,3 m): ${M.WIND_HEIGHT_FACTOR.toFixed(3)}`);
process.exit(fail ? 1 : 0);
