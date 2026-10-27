# Цели громкости для площадок

Состояние на 2026-10-27. «Офиц.» — из документации площадки; «вторичн.» —
из статей студий и сервисов мастеринга, официального подтверждения нет.

| Площадка | Интегральная громкость | True peak | Источник |
|---|---|---|---|
| Spotify | −14 LUFS (режимы слушателя: Loud −11, Normal −14, Quiet −19) | ≤ −1 dBTP; для мастеров громче −14 LUFS — ≤ −2 dBTP | офиц. |
| Apple Music (Sound Check) | −16 LUFS; громкие треки убавляет, тихие не прибавляет | ≤ −1 dBTP | вторичн. |
| YouTube | −14 LUFS; громкие убавляет, тихие не прибавляет | ≤ −1 dBTP | вторичн. |
| Deezer | ~−15 LUFS | ≤ −1 dBTP | вторичн. |
| Tidal | ~−14 LUFS | ≤ −1 dBTP | вторичн. |
| Яндекс Музыка | ~−14 LUFS (нормализует громкость) | ≤ −1 dBTP | вторичн., официальных требований не найдено |
| VK Музыка | ~−14 LUFS | ≤ −1 dBTP | вторичн., официальных требований не найдено |

## Практический вывод

- Универсальный компромисс: **около −14 LUFS, true peak ≤ −1 dBTP**.
  Apple убавит такой трек примерно на 2 дБ — это нормально.
- Делать громче −14 LUFS имеет смысл только ради звучания (плотность
  жанра), а не ради громкости на площадке: громкий мастер всё равно
  убавят, а сжатие останется. Если громче — true peak ≤ −2 dBTP.
- Веб-плеер Spotify и сторонние устройства нормализацию не используют —
  слушатель услышит мастер как есть.
- Перед релизом сверить требования в кабинете дистрибьютора.

## Источники

- [Spotify: Loudness normalization](https://support.spotify.com/au/artists/article/loudness-normalization/) — офиц.
- [Fora Soft: LUFS targets per platform 2026](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026)
- [RoEx: What LUFS should I master at](https://www.roexaudio.com/blog/what-lufs-should-i-master-at)
- [Mastering The Mix: Mastering for SoundCloud, Apple Music, Spotify, YouTube](https://masteringthemix.com/blogs/learn/76296773-mastering-audio-for-soundcloud-itunes-spotify-and-youtube)
- [Arefyev Studio: мастеринг для Яндекс Музыки](https://arefyevstudio.com/mastering-dlya-yandex-music/)
- [Arefyev Studio: мастеринг для VK Музыки](https://arefyevstudio.com/mastering-dlya-vk-music/)
- [push-music: калькулятор LUFS](https://push-music.ru/tools/loudness-calculator)
