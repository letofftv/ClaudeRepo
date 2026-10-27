# Карта плагинов: что за что отвечает и чем заменить бесплатно

Состояние на 2026-10-27; цены и версии — по поисковой выдаче, сайты
вендоров из песочницы не открывались. **Покупка из России:** российские
карты в западных магазинах не проходят; Native Instruments не продаёт в
Россию с 2022; **Voxengo принимает российские карты в рублях** (заявление
2024 г.); Valhalla — недорого, серийный номер. Серые «лицензии» с
маркетплейсов отзывают. Пиратство не рассматривается.

**Apple Silicon:** ставить только нативные плагины — Rosetta уходит
(общий режим до macOS 27). Intel-only, пропустить: Limiter No6, TDR
Kotelnikov, GSnap.

**Управление из Claude:** простые плагины с короткими списками
параметров (Trackspacer, LALA/FETish, T-De-Esser 2, Valhalla, LoudMax)
агенту удобнее; Serum, Vital, Ozone, Pro-Q 4, Melda — сотни параметров,
видны только через Configure (до 128).

## Сначала поставить (бесплатно)

1. Valhalla Supermassive, Freq Echo, Space Modulator — реверб и дилеи.
2. TDR Nova — динамический EQ (резонансы, сайдчейн-провалы).
3. Analog Obsession LALA (LA-2A) и FETish (1176) — компрессоры вокала.
4. Techivation T-De-Esser 2 — деэссер.
5. Youlean Loudness Meter 2 и Voxengo SPAN — громкость и спектр.
6. Airwindows Consolidated — 500+ алгоритмов (сатурация, консоли, лимитеры).
7. ANINA (CRQL) — спектральный «укротитель» резонансов, аналог soothe; есть сайдчейн.
8. Venn Free Suite (в т.ч. Free Clip 2) — клиппер для мастера.

По желанию: Kilohearts Essentials (нужен аккаунт), MeldaProduction
MFreeFXBundle, Softube Saturation Knob, Graillon 3 (бесплатная редакция
с коррекцией высоты), Bertom Denoiser Classic (плати сколько хочешь).

## Вокал

| Задача | Платно | Бесплатно / встроено в Live |
|---|---|---|
| Тюнинг офлайн | Melodyne 5 (Essential ~$99) | Auto Shift (Live 12.1+), Graillon 3 |
| Тюнинг в реальном времени | AutoTune 2026 / Pro 11 | Auto Shift, Graillon 3 |
| Компрессия | FabFilter Pro-C 3, CLA-76/CLA-2A | LALA → FETish, Compressor, Glue Compressor |
| Деэссер | FabFilter Pro-DS | T-De-Esser 2 |
| Резонансы | soothe3 ($259, тяжёлый по CPU) | ANINA, TDR Nova |
| EQ | Pro-Q 4 | EQ Eight, TDR Nova |
| Сатурация | Soundtoys Decapitator | Saturator, Roar (Suite), Saturation Knob, Klanghelm IVGI, Airwindows |
| Реверб / дилей | Valhalla VintageVerb, ValhallaDelay ($50 каждый), EchoBoy | Supermassive, Freq Echo, Echo, Hybrid Reverb (Suite) |
| Вокальный «комбайн» | iZotope Nectar 4 | цепочка из встроенных |
| Реально купить из РФ | Valhalla; Voxengo (Voxformer, Soniformer, GlissEQ, Teote, Elephant) | — |

## Вписать вокал в готовую минусовку

| Платно | Бесплатно |
|---|---|
| Wavesfactory Trackspacer (~$59) — сайдчейн-провал в минусовке по вокалу | ANINA с сайдчейном; TDR Nova с сайдчейном (1–4 кГц, 1–3 дБ); EQ Eight + Compressor/Multiband Dynamics с сайдчейном |
| Gullfoss, Neutron 5 Unmask | — |

## Чистка

| Платно | Бесплатно |
|---|---|
| iZotope RX 12 (Dialogue Isolate, De-reverb) | Bertom Denoiser Classic; Stem Separation в Live Suite 12.3+. Хорошего бесплатного де-реверба нет |

## Мастеринг и замеры

| Платно | Бесплатно / встроено |
|---|---|
| iZotope Ozone 12 (Unlimiter в Advanced — восстанавливает динамику пережатых минусовок) | EQ Eight (M/S), Glue Compressor, Multiband Dynamics, Limiter (true peak) |
| FabFilter Pro-L 2, Pro-MB | LoudMax (Apple Silicon — не подтверждено), Venn Free Clip 2 |
| ADPTR Metric AB (референс) | групповая шина + референс в мастер, выравнивание по Youlean |
| iZotope Insight 2 | Youlean, SPAN |

## Инструменты для сочинения

| Платно | Бесплатно |
|---|---|
| Serum 2 ($249), Omnisphere 3 ($499), Arturia V Collection 11, Komplete 15 / Kontakt 8 (в РФ не продаётся) | Vital, Surge XT, Splice INSTRUMENT (вместо LABS), Decent Sampler, Dexed, TAL-NoiseMaker, OTT |

## Встроенное в Ableton Live 12 (редакции)

- **Все редакции:** Auto Shift (коррекция высоты, гармонии по MIDI),
  Drift, Expressive Chords, EQ Eight, Compressor, Limiter, Utility, Tuner,
  Auto Filter, MIDI-инструменты и учёт тональности.
- **Standard и выше:** Glue Compressor, Multiband Dynamics, Vocoder, Echo, Spectrum.
- **Только Suite:** Roar, Meld, Granulator III, Hybrid Reverb, Spectral
  Resonator/Time, **Stem Separation** (12.3+), Max for Live (нужен Producer Pal).
- Live 12.4.5 — актуальная (2026-08). ARA нет.

Источники — в `research/2026-10-27-audio-production.md`.
