#!/usr/bin/env bash
# Read-only inventory of the server before moving from WSL2 to native Ubuntu.
# Changes nothing, prints no secrets (only paths of env files, never contents).
# The report stays on the server: it has addresses and names — never commit it.
#
#   bash inventory.sh > ~/hub-ops/migration/inventory-$(date +%F).md
#
# Run as the user that runs the farm and the hub (on this server: root).
set -u
T="timeout 20"

section() { printf '\n## %s\n\n' "$1"; }
run() {  # title, command...
  local title="$1"; shift
  printf '### %s\n\n```\n' "$title"
  $T "$@" 2>&1 | head -n 200
  printf '```\n\n'
}
have() { command -v "$1" >/dev/null 2>&1; }
strip_creds() { sed -E 's#(https?://)[^/@ ]+@#\1#g'; }

printf '# Инвентаризация сервера — %s\n\n' "$(date '+%F %T')"
printf 'Только чтение. Отчёт остаётся на сервере: в нём адреса и имена.\n'

section "Система"
run "ОС и ядро" bash -c 'grep PRETTY_NAME /etc/os-release; uname -r; grep -qi microsoft /proc/sys/kernel/osrelease && echo "WSL2: да" || echo "WSL2: нет"'
run "Память" free -h
run "Диски и разделы" lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
run "Место" df -hT -x tmpfs -x devtmpfs -x squashfs -x overlay
run "Самые большие папки в домашней" bash -c 'du -xsh "$HOME"/* "$HOME"/.[!.]* 2>/dev/null | sort -h | tail -25'

section "Видеокарта"
if have nvidia-smi || [ -x /usr/lib/wsl/lib/nvidia-smi ]; then
  SMI=$(command -v nvidia-smi || echo /usr/lib/wsl/lib/nvidia-smi)
  run "nvidia-smi" "$SMI" --query-gpu=name,driver_version,memory.used,memory.total --format=csv
  run "Процессы на видеокарте" "$SMI" --query-compute-apps=pid,process_name,used_memory --format=csv
else
  echo "nvidia-smi не найден"
fi

section "Docker"
if have docker; then
  run "Движок (Docker Desktop или свой)" docker info --format 'ОС движка: {{.OperatingSystem}} · версия {{.ServerVersion}} · корень {{.DockerRootDir}} · рантаймы: {{range $k, $v := .Runtimes}}{{$k}} {{end}}'
  run "Контейнеры" docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
  run "Контейнеры: compose-проект, папка, перезапуск, тома" bash -c '
    for c in $(docker ps -aq); do
      docker inspect -f "{{.Name}} | проект={{index .Config.Labels \"com.docker.compose.project\"}} | папка={{index .Config.Labels \"com.docker.compose.project.working_dir\"}} | файлы={{index .Config.Labels \"com.docker.compose.project.config_files\"}} | restart={{.HostConfig.RestartPolicy.Name}} | gpu={{.HostConfig.DeviceRequests}} | тома: {{range .Mounts}}{{.Type}}:{{if .Name}}{{.Name}}{{else}}{{.Source}}{{end}}->{{.Destination}} {{end}}" "$c"
    done'
  run "Тома" docker volume ls
  run "Образы (без RepoDigests — собраны локально, их сохранить через docker save)" bash -c '
    docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.ID}}" | while IFS=$(printf "\t") read -r ref size id; do
      d=$(docker image inspect -f "{{len .RepoDigests}}" "$id" 2>/dev/null)
      [ "$d" = "0" ] && mark="ЛОКАЛЬНЫЙ" || mark="из реестра"
      printf "%s\t%s\t%s\n" "$ref" "$size" "$mark"
    done'
  run "Занято Docker" docker system df
else
  echo "docker не найден"
fi

section "Службы и расписания"
run "systemd: свои системные службы (/etc/systemd/system)" bash -c 'ls -1 /etc/systemd/system/*.service /etc/systemd/system/*.timer 2>/dev/null'
run "systemd: включённые пользовательские юниты" systemctl --user list-unit-files --state=enabled --no-pager
run "systemd: таймеры" systemctl list-timers --all --no-pager
run "cron" bash -c 'crontab -l 2>&1; ls -la /etc/cron.d 2>/dev/null'
run "Слушающие порты" bash -c 'ss -ltnpH 2>/dev/null | awk "{print \$4, \$6}" | sort -u'
run "Долгоживущие процессы (python, node, ollama, chrome, ffmpeg)" bash -c 'ps -eo pid,etime,comm,args --sort=-etime | grep -Ei "python|node|ollama|chrom|ffmpeg|redis|postgres" | grep -v grep | cut -c1-200 | head -40'

section "Программы"
run "pipx" bash -c 'pipx list --short 2>&1'
run "npm -g" bash -c 'npm ls -g --depth=0 2>&1'
run "ffmpeg" bash -c 'ffmpeg -hide_banner -version | head -1; ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "nvenc" '
run "Ollama: модели" bash -c 'ollama list 2>&1 || curl -s -m 5 http://127.0.0.1:11434/api/tags'
run "Claude Code" bash -c 'claude --version 2>&1; ls -d "$HOME"/.claude "$HOME"/hub-ops 2>&1'

section "Код и настройки"
run "Git-репозитории (до 4 уровней от домашней папки)" bash -c '
  find "$HOME" /srv /opt -maxdepth 4 -name .git -type d 2>/dev/null | while read -r g; do
    r=$(dirname "$g"); url=$(git -C "$r" remote get-url origin 2>/dev/null | sed -E "s#(https?://)[^/@ ]+@#\1#")
    dirty=$(git -C "$r" status --porcelain 2>/dev/null | wc -l)
    printf "%s | %s | изменённых файлов: %s\n" "$r" "${url:-нет origin}" "$dirty"
  done'
run "Файлы с секретами (только пути, содержимое не читается)" bash -c '
  find "$HOME" /srv /opt -maxdepth 5 \( -name ".env" -o -name "*.env" -o -name "env" -path "*/.config/*" -o -name "*secret*" -o -name "*.pem" -o -name "id_*" \) -type f 2>/dev/null | grep -v -E "/node_modules/|/\.cache/|/site-packages/" | head -60'
run "Пульт: настройки вне git" bash -c 'ls -la "$HOME"/ClaudeRepo/app/config/hub.json "$HOME"/ClaudeRepo/app/config/tools.local.json "$HOME"/.config/hub/env 2>&1; du -sh "$HOME"/hub-work 2>/dev/null; du -sh "$HOME"/hub-work/models/* 2>/dev/null'

section "Windows (через WSL interop)"
if have powershell.exe; then
  PS="powershell.exe -NoProfile -NonInteractive -Command"
  run "Режим загрузки (UEFI / Legacy)" $PS '(Get-ComputerInfo -Property BiosFirmwareType).BiosFirmwareType'
  run "Быстрый запуск Windows (HiberbootEnabled: 1 — включён, мешает дискам NTFS из Ubuntu)" reg.exe query 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power' /v HiberbootEnabled
  run "BitLocker (нужны права администратора — иначе «отказано»)" manage-bde.exe -status
  run "Диски Windows" $PS 'Get-PhysicalDisk | Format-Table -AutoSize FriendlyName,MediaType,Size; Get-Volume | Where-Object DriveLetter | Format-Table -AutoSize DriveLetter,FileSystemLabel,FileSystem,Size,SizeRemaining'
  run "Задачи планировщика (не Microsoft)" $PS 'Get-ScheduledTask | Where-Object { $_.TaskPath -notlike "\Microsoft\*" } | ForEach-Object { "{0}{1} | {2} | {3} {4}" -f $_.TaskPath, $_.TaskName, $_.State, $_.Actions.Execute, $_.Actions.Arguments }'
  run "Проброс портов в WSL" netsh.exe interface portproxy show all
  run "Свои правила брандмауэра (входящие, включённые)" $PS 'Get-NetFirewallRule -Direction Inbound -Enabled True | Where-Object { -not $_.DisplayGroup } | Format-Table -AutoSize DisplayName,Action,Profile'
  run ".wslconfig" $PS 'Get-Content "$env:USERPROFILE\.wslconfig" -ErrorAction SilentlyContinue'
  run "Службы с автозапуском не от Microsoft" $PS 'Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq "Auto" -and $_.PathName -notmatch "\\Windows\\" } | Format-Table -AutoSize Name,State,PathName'
else
  echo "powershell.exe недоступен — не WSL или выключен interop"
fi

printf '\n---\nГотово. Секреты не читались; перед пересылкой куда-либо убрать адреса и имена.\n'
