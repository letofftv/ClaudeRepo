# GTX 1050 Ti при переезде с Windows на Ubuntu

Заметка 2026-10-26: что важно для видеокарты и ИИ-инструментов фабрики при
переезде. Метки: **[стр]** — прочитано на странице, **[поиск]** — только из
поисковой выдачи, **[память]** — не перепроверено. Ничего не проверялось на
живой системе.

## Драйвер

- **Ставить проприетарный `nvidia-driver-580`, не `nvidia-driver-580-open`.**
  Открытые модули ядра работают только с Turing и новее; для Maxwell, Pascal и
  Volta нужен проприетарный вариант [поиск: руководство NVIDIA по модулям ядра].
  Оба варианта одновременно ставить нельзя.
- `ubuntu-drivers` может предложить не тот вариант — сначала посмотреть
  `ubuntu-drivers devices`, затем ставить пакет явно:
  `sudo apt install nvidia-driver-580`. После установки проверить
  `/proc/driver/nvidia/version` — там не должно быть «Open Kernel Module».
- Ставить **из репозитория Ubuntu**, не .run-установщиком NVIDIA: Ubuntu
  собирает подписанные модули под свои ядра. В Ubuntu 26.04 пакеты 580 есть в
  updates/security (580.173–580.178) [поиск: Launchpad, ubuntuupdates].
- Ветка 580 — последняя для Pascal. Для GeForce на Pascal NVIDIA обещает
  ежеквартальные обновления безопасности до октября 2028 [поиск] — горизонт
  жизни этой карты на Linux.

## Ядро

- Есть сообщения пользователей, что драйвер 580 **не собирается с ядром 7.0**
  (Proxmox / Debian 13, из-за изменений API ядра) [поиск: форум Proxmox].
  Для Ubuntu это не подтверждено и не опровергнуто.
- Поэтому: ядро — только из репозитория Ubuntu; перед обновлением ядра
  убедиться, что для него есть модуль `linux-modules-nvidia-580-…`; оставить
  в загрузчике предыдущее ядро на случай отката.
- Самый консервативный вариант — Ubuntu 24.04 LTS (давно проверенная связка с
  580). Ubuntu 26.04 LTS — пакеты есть, но связку с новым ядром проверить
  сразу после установки (`nvidia-smi`).

## Docker и CUDA

- Docker + NVIDIA Container Toolkit: совместимость с картой определяется
  драйвером, а не версией тулкита; CUDA Toolkit на хост ставить не нужно
  [поиск: документация Container Toolkit].
- Образы брать под **CUDA 12** (`:cuda12`, `cuda-12.6`), не `:cuda13` — CUDA 13
  не поддерживает Pascal. Пример: qwentts.cpp `:cuda12` собран для sm_61 [стр].
- PyTorch — только cu126 и не новее 2.14 (см. `CLAUDE.md`).

## Чем Linux отличается от Windows для этой карты

- **Нет подкачки видеопамяти в ОЗУ.** На Windows драйвер при нехватке 4 ГБ
  выгружает данные в оперативную память — медленно, но работает. На Linux —
  ошибка нехватки памяти и падение [поиск]. После переезда брать более
  сжатые варианты моделей (Q4 вместо Q8) и следить за `nvidia-smi`.
- На Linux лучше работают Playwright, headless Chrome для HyperFrames и
  Docker-образы инструментов из находок.
- 16 ГБ ОЗУ: хватает для всего из рекомендованного набора (озвучка, субтитры,
  Video2X, SD1.5); тесно для SDXL с hires fix (в замере на 1050 Ti уходило
  21–26 ГБ) и для разгрузки больших моделей. Апгрейд до 32 ГБ полезен, но не
  срочен [оценка].

## До переезда (Windows)

- CUDA в WSL2 поддерживает Pascal (GeForce в режиме WDDM); Docker Desktop с
  GPU работает через NVIDIA Container Toolkit [поиск: NVIDIA CUDA on WSL User
  Guide] — образы `:cuda12` можно опробовать уже сейчас.
- Нативные Windows-сборки: whisper.cpp (CUDA 12.4 / 11.8), ComfyUI portable
  `cu126`, Video2X, скрипт сборки qwentts.cpp `buildcuda.cmd` [стр].
- Проверенные на Windows настройки не переносить на Linux вслепую: из-за
  отсутствия подкачки видеопамяти то, что «влезало» на Windows, на Linux может
  падать.

## Источники

- [NVIDIA: модули ядра (open vs proprietary)](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/latest/kernel-modules.html)
- [Launchpad: nvidia-graphics-drivers-580](https://launchpad.net/ubuntu/+source/nvidia-graphics-drivers-580)
- [ubuntuupdates: nvidia-kernel-source-580 (26.04)](https://ubuntuupdates.org/package/core/resolute/restricted/base/nvidia-kernel-source-580)
- [LinuxCapable: драйверы NVIDIA на Ubuntu 26.04/24.04](https://linuxcapable.com/install-nvidia-drivers-on-ubuntu-linux/)
- [Форум NVIDIA: 1050 Ti пропадает при open-модуле](https://forums.developer.nvidia.com/t/dual-gpu-setup-rtx-5060-ti-gtx-1050-ti-not-working-on-linux-with-nvidia-580/358244)
- [Форум Proxmox: 580 и ядро 7.0](https://forum.proxmox.com/threads/nvidia-580-x-kernel-7-0-incompatibility-on-trixie.183421/latest)
- [igor'sLAB: Arch переводит Pascal на legacy](https://www.igorslab.de/en/arch-linux-is-phasing-out-pascal-gtx-10-cards-are-being-removed-from-the-default-path-with-nvidia-590/)
- [NVIDIA: CUDA on WSL User Guide](https://docs.nvidia.com/cuda/archive/13.1.1/wsl-user-guide/index.html)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/1.13.1/index.html)
