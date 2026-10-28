# Промпт: сервер на новой Ubuntu (Claude на сервере)

Вставить в Claude Code на новой Ubuntu, запущенный из `~/hub-ops`:

> Прочитай и выполни
> https://raw.githubusercontent.com/letofftv/ClaudeRepo/main/common/ubuntu-migration/prompt-after.md

---

## Промпт

Ты — оператор домашнего сервера. Только что поставлена **Ubuntu Server
24.04 LTS** на отдельном SSD; раньше всё работало в WSL2 на Windows 10, и
тот диск остался нетронутым как откат. Перед переездом оператор сделал
опись, план и резервные копии на HDD: папка `migration-<дата>/` на HDD,
в ней `README.md`, а также `plan.md` и `inventory-*.md` из `~/hub-ops`.

План переезда:
https://raw.githubusercontent.com/letofftv/ClaudeRepo/main/common/ubuntu-migration/README.md
Правила видеокарты и всё о фабрике:
https://raw.githubusercontent.com/letofftv/ClaudeRepo/main/CLAUDE.md
(разделы «Сервер», «Ограничения видеокарты»).

### Правила

1. **Спрашивать владельца перед:**
   - установкой драйвера и каждой перезагрузкой;
   - включением брандмауэра — назвать подсети;
   - удалением чего-либо;
   - всем, что трогает диск с Windows.

   Одним списком: что, зачем, чем рискуем.
2. **Видеокарта:**
   - только `nvidia-driver-580` из репозитория Ubuntu — не `-open`, не
     `-server-open`, не `.run`;
   - CUDA Toolkit на хост не ставить;
   - Docker-образы — под CUDA 12, не 13;
   - PyTorch — только cu126 и не новее 2.14.
3. **Диски:**
   - диск с Windows не монтировать на запись и не форматировать;
   - HDD не форматировать;
   - базы и тома Docker держать на SSD с Ubuntu, не на NTFS.
4. **Секреты:** `.env` и токены восстанавливать как файлы с правами 600,
   не печатать; в отчёт для песочницы — без адресов и имён.
5. **Всё запускать от обычного пользователя,** которого создал установщик
   (группа `docker`), а не от root, как было в WSL.
6. Если для работы нужна правка кода в репозитории — не чинить на месте,
   а записать в отчёт.

### Шаг 1. Система

- `sudo apt update && sudo apt full-upgrade`.
- **Ядро должно быть GA 6.8.** `uname -r` → `6.8.0-…`, установлен
  `linux-generic`, а не `linux-generic-hwe-24.04`.
  - HWE в 24.04.5 — Linux 7.0, с которым у драйвера 580 есть проблемы.
  - Если стоит HWE: предложить `sudo apt install linux-generic`,
    перезагрузиться в 6.8 и только потом убрать HWE.
  - Старое ядро в загрузчике оставить.
- Часовой пояс владельца. Обновления безопасности
  (`unattended-upgrades`) — как по умолчанию.
- **SSH:**
  - убедиться, что вход с мака по ключу работает;
  - только после этого `PasswordAuthentication no`;
  - `authorized_keys` есть в резервной копии.

### Шаг 2. Драйвер

```
sudo apt install -y ubuntu-drivers-common
ubuntu-drivers list                   # среди вариантов — nvidia-driver-580 (без -open)
sudo ubuntu-drivers install nvidia:580
```

После перезагрузки (с разрешения):
- `nvidia-smi` видит GTX 1050 Ti и драйвер 580;
- в `/proc/driver/nvidia/version` нет «Open Kernel Module»;
- `dpkg -l | grep -E 'nvidia.*open'` — пусто.

Если включён Secure Boot и система попросит пароль MOK — сказать
владельцу: после перезагрузки на экране MOK выбрать «Enroll MOK».

### Шаг 3. Диски

- **HDD с резервными копиями** (NTFS) — в `/etc/fstab` по UUID:

  ```
  UUID=<uuid> /mnt/hdd ntfs3 nofail,uid=<uid>,gid=<gid>,umask=022 0 0
  ```

  Если монтируется только на чтение или «dirty», значит, в Windows
  остался быстрый запуск. Сказать владельцу, сам не чинить.
- **Диск с Windows** не монтировать (или только `ro`, если владелец
  попросит).

### Шаг 4. Docker с видеокартой

1. **Docker Engine** — из репозитория Docker, без snap:

   ```
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list
   sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker "$USER"
   ```

   Если download.docker.com закрыт — `sudo apt install docker.io
   docker-compose-v2` из репозитория Ubuntu.
2. **NVIDIA Container Toolkit.** Если nvidia.github.io закрыт, ставить
   `.deb` с мака, в отчёте шага 0 сказано, что скачать.

   ```
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt update && sudo apt install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
   docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
   ```

3. **Docker обходит `ufw`.** Опубликованный порт (`-p 5432:5432`) открыт
   наружу, даже если брандмауэр его закрывает. Поэтому в compose
   публиковать только то, к чему ходят снаружи, и с адресом:
   `127.0.0.1:5432:5432` для локальных служб.

### Шаг 5. Службы по плану

Порядок — из `plan.md`: сначала базы, потом то, что от них зависит.

- **Postgres** — тот же тег образа и та же версия pgvector, что
  записаны в плане. Поднять пустую базу и восстановить дамп:
  `zstd -dc postgres.sql.zst | docker exec -i <контейнер> psql -U <пользователь>`.
  Проверить число таблиц и строк в главных таблицах.
- **Redis** — если в копии есть `dump.rdb` / `appendonly`, положить их в
  том до первого запуска.
- **Образы:**
  - сохранённые — `zstd -dc images/<имя>.tar.zst | docker load`, в том
    числе Whisper фабрики;
  - остальные — скачать заново.
- **Тома** — распаковать через вспомогательный контейнер.
- **Ollama** — модели из списка.
- **Ферма, линия нарезки, «руки» Джарвиса:**
  - вернуть код и `.env` в те же папки (домашняя теперь
    `/home/<пользователь>`);
  - запуск — compose `restart: unless-stopped` или пользовательские
    службы systemd с `loginctl enable-linger`;
  - задача Windows, которая держала WSL, больше не нужна.
- **Каждую службу проверять сразу:** порт отвечает, логи без ошибок.

### Шаг 6. Программы

- `sudo apt install -y ffmpeg pipx git` → `ffmpeg -encoders | grep nvenc`
  (h264_nvenc, hevc_nvenc).
- Инструменты пульта через pipx — по описи:
  - `auto-editor`;
  - `scenedetect[opencv-headless]`;
  - `piper-tts`;
  - `audio-separator` — строго по рецепту из
    https://raw.githubusercontent.com/letofftv/ClaudeRepo/main/audio/finds/audio-separator.md
    (torch 2.14.1 из индекса cu126, `audioread`, компилятор C только на
    время установки).
- Node, Playwright, Chromium для фермы — по её собственной инструкции.
  У Claude фабрики есть пакет о переезде.

### Шаг 7. Пульт

По `~/ClaudeRepo/app/deploy/server-prompt.md`, шаги 2–5, но с
настройками из копии, а не с нуля:

- **Клон и тесты:** `git clone`, затем `python3 -m unittest discover -s tests`.
- **Настройки:** вернуть `config/hub.json`, `config/tools.local.json`,
  `~/.config/hub/env` (токен прежний — тогда мак, мост и браузер не надо
  перенастраивать), `~/hub-ops`, `~/hub-work/models`.
- **Поправить в `hub.json`:**
  - `bind` — новый адрес в домашней сети или VPN;
  - `hide_disks` и `disks` — по новым точкам монтирования;
  - `services` — как теперь запущены службы. Было «задача Windows» —
    станет systemd или docker.
- **`tools.local.json`:**
  - команда `whisper` (`docker run --gpus all …`) обычно подходит как
    есть;
  - пути `separator_models` и `piper_voices` — через `{workdir}`.
- **Юниты:** `hub.service`, `hub-update.service`, `hub-update.timer` —
  по шапке `deploy/hub.service`, плюс `loginctl enable-linger`.
- **Брандмауэр:**
  1. `sudo ufw allow from <подсеть> to any port 22 proto tcp`;
  2. то же для 8787 и для портов, на которые ходят мак и Джарвис;
  3. только потом `sudo ufw enable`. SSH разрешить первым, иначе связь
     пропадёт.

### Шаг 8. Проверка и замеры «после»

1. **Пульт:**
   - `/healthz`;
   - «Инструментов доступно: N из M» в журнале службы;
   - панель «Сервер» без лишних тревог;
   - на Ubuntu должны появиться питание и память по процессам.
2. **Те же замеры, что «до»** (условия — в `plan.md`):
   - сцена фермы — секунд на кадр и пик видеопамяти;
   - `whisper`, `stems`, `vertical_9x16` на видеокарте и на процессоре.
3. **Откат на процессор при нехватке видеопамяти.** На Linux видеопамять
   в ОЗУ не уходит. Проверить `stems`, когда другой процесс занял ~3,5
   ГБ. Ожидание: ошибка «out of memory» и повтор на процессоре, в
   карточке задачи — «видеокарта не справилась».
4. **Vulkan:** `sudo apt install -y vulkan-tools && vulkaninfo --summary`
   → видна GTX 1050 Ti. Video2X без разрешения не ставить — просто
   сообщить, что теперь можно.
5. **Внешние клиенты:**
   - мост MCP с мака (`hub_status`);
   - задание от Джарвиса доходит до фермы — новый адрес вписывает
     владелец.

### Шаг 9. Отчёт

1. **Владельцу коротко:**
   - что работает;
   - что не поднялось и почему;
   - сравнение «до/после»;
   - что вписать на маке и у Джарвиса.
2. **Блок для песочницы**, без адресов, имён и секретов:

```
Ответ для песочницы — переезд на Ubuntu, <дата>, пульт <версия>, коммит <hash>
Система: Ubuntu <версия>, ядро <uname -r>, Secure Boot вкл/выкл; драйвер <версия> (не open: да)
Docker <версия> + Container Toolkit <версия>; тест cuda:12.6 nvidia-smi: ок/нет
Службы: <служба — запущена как — проверка>; не поднялось: <что и почему>
Панель: питание да/нет; память по процессам да/нет; лишние тревоги <...>
Замеры до → после: ферма <с/кадр>; whisper <с>; stems <с>; vertical_9x16 GPU/CPU <с>
Нехватка видеопамяти: stems → откат на процессор да/нет (что в логе)
Vulkan: видна карта да/нет
Инструменты пульта: доступно N из M; не работают: <id — причина>
Нужна правка кода в репозитории: <что> или «нет»
Неясно / вопросы: <...>
```

Когда всё работает неделю-две, предложить владельцу, что делать с WSL и
Windows. Пока он не решил, ничего не удалять.
