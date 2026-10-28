# whisper.cpp на CUDA 12 для HyperFrames

- **Ссылка:** https://github.com/ggml-org/whisper.cpp
- **Что это:** распознавание речи для субтитров — уже встроено в HyperFrames и Orkas, но по умолчанию работает только на процессоре
- **Найдено:** 2026-10-26, исследование субтитров
- **Статус:** не нужно — на фабрике уже работает Whisper на видеокарте с таймкодами слов: faster-whisper large-v3-turbo int8 в Docker (отчёт оператора 2026-10-28; в пульт подключён обёрткой `app/tools/whisper_subs.py`). Если появится HyperFrames или Orkas — направить их на существующий Whisper, а не собирать второй

## Зачем фабрике

- HyperFrames по умолчанию собирает whisper.cpp **без GPU** и берёт модель
  `small.en` (английская). Для русских субтитров на видеокарте нужна своя
  сборка и другая модель.
- Сборка с `-DGGML_CUDA=1` на CUDA 12.x: архитектура 61 (Pascal) добавляется
  автоматически при CUDA < 13. Путь к бинарнику — в `HYPERFRAMES_WHISPER_PATH`.
- Модель: **large-v3-turbo** (квантованная q5_0/q8_0) или medium (~2,1 ГБ).
  large-v3 (~3,9 ГБ) на 4 ГБ впритык.

## Риски и оговорки

- MIT. Официальный Docker-образ `main-cuda` — CUDA 13, архитектуры от 75:
  **на Pascal не работает**, собирать самому. На Windows официальные сборки —
  CUDA 12.4 и 11.8.
- Сравнения turbo / medium на русском не найдено — сделать A/B.
- Альтернативы: Parakeet TDT 0.6B v3 (встроен в HyperFrames, CPU, русский) и
  GigaAM (`video/finds/gigaam.md`).

## Как подключить

На сервере (Linux):

```
cmake -B build -DGGML_CUDA=1 && cmake --build build -j --config Release
# затем HYPERFRAMES_WHISPER_PATH=<путь к whisper-cli>
```

## Что проверено

В исследовании прочитаны `whisper/manager.ts` HyperFrames (сборка без GPU,
`small.en`), Dockerfile `main-cuda` и release.yml whisper.cpp, таблица памяти
моделей в README. Не собиралось.
