# Цифровизация бизнеса

Автоматизация процессов, CRM и учёт, торговля на маркетплейсах, платежи,
аналитика, клиентские боты, документы. Личные задачи и заметки — в
[`productivity/`](../productivity/README.md); написание кода — в [`coding/`](../coding/README.md).

Контекст: малый бизнес в России. Западные SaaS (Zapier, Make, HubSpot, n8n
Cloud) недоступны или их нельзя оплатить, поэтому упор на **российскую
экосистему** (Bitrix24, 1С, МойСклад, ЮKassa, Wildberries/Ozon/Яндекс Маркет,
Яндекс Метрика, Telegram, MAX) и **свой сервер** (n8n, Postgres).

## Стартовый набор (≤6)

1. **[n8n на домашнем сервере](finds/n8n.md) + встроенный MCP +
   [n8n-io/skills](finds/n8n-skills.md)** — все интеграции через n8n, ключи
   там же; Claude проектирует воркфлоу, не видя токенов.
2. **[Bitrix24](finds/bitrix24-mcp.md)** как основная CRM — бесплатный тариф,
   официальный docs-MCP и вебхуки; data-MCP — после проверки на своём
   портале. amoCRM — только если продажи идут через чаты (официального MCP нет).
3. **[Бот на aiogram + ЮKassa](finds/telegram-bot-stack.md)** — Claude Code
   пишет бота, бот передаёт события в n8n.
4. **[small-business-ru](finds/small-business-ru.md), выборочно** — проверка
   контрагентов по ИНН, налоговый календарь, счета, договоры.
5. **[document-skills](../productivity/finds/document-skills.md)** — счета,
   акты, КП и договоры по шаблонам.
6. **Аналитика только на чтение** — Яндекс Метрика (yandex-metrica-mcp) и
   свой Postgres (mcp-toolbox под read-only ролью); Metabase — позже.

По ситуации: [marketplaces-mcp-ru](finds/marketplaces-mcp-ru.md) (WB, Ozon,
Яндекс Маркет, Авито), [1c-odata-mcp](finds/1c-odata-mcp.md) (1С),
[moysklad-mcp-ru](https://github.com/ilyautov/moysklad-mcp-ru) (МойСклад).

## Общие правила

- Подключать **сначала с токенами только на чтение**. Запись — через
  воркфлоу n8n с подтверждением владельца в Telegram.
- MCP к российским сервисам запускать **локально в Claude Code на маке
  (stdio)**, а не удалёнными коннекторами claude.ai: те вызываются из облака
  Anthropic — свой сервер пришлось бы выставлять в интернет, а часть
  российских сайтов блокирует зарубежные адреса.
- **Персональные данные клиентов**, которые Claude читает из CRM, — это
  трансграничная передача по 152-ФЗ: минимизировать или обезличивать.
- Ключи и токены — в n8n или в коде бота, **не в этом публичном репозитории**.

## Лучшее (2026-10-27)

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [n8n + встроенный MCP](finds/n8n.md) | платформа (свой сервер) | хребет автоматизации | **взять** |
| 2 | [n8n-io/skills](finds/n8n-skills.md) | плагин (официальный) | правильные воркфлоу n8n | **взять** |
| 3 | [document-skills](../productivity/finds/document-skills.md) | навыки (официальные) | счета, акты, КП, договоры, OCR | **взять** |
| 4 | [Bitrix24 docs-MCP](finds/bitrix24-mcp.md) | MCP (официальный) | интеграции без выдуманных методов | **взять** |
| 5 | [aiogram + ЮKassa](finds/telegram-bot-stack.md) | библиотеки | клиентский бот с оплатой | **взять** |
| 6 | [Bitrix24 data-MCP](finds/bitrix24-mcp.md) | MCP (официальный) | CRM и задачи обычным языком | **попробовать** (на своём портале) |
| 7 | [small-business-ru](finds/small-business-ru.md) | 34 навыка | налоги, контрагенты, договоры по РФ | **попробовать** (выборочно) |
| 8 | [1c-odata-mcp](finds/1c-odata-mcp.md) | MCP | вопросы к 1С, только чтение | **попробовать** (если есть 1С) |
| 9 | [moysklad-mcp-ru](https://github.com/ilyautov/moysklad-mcp-ru) | MCP | МойСклад: остатки, заказы; запись выключена | **попробовать** (если МойСклад) |
| 10 | [marketplaces-mcp-ru](finds/marketplaces-mcp-ru.md) | MCP | WB, Ozon, Яндекс Маркет, Авито | **попробовать** (если маркетплейсы) |
| 11 | [yandex-metrica-mcp](https://github.com/BoxLab-Ltd/yandex-metrica-mcp) | MCP | отчёты Метрики, только чтение | **попробовать** |
| 12 | [mcp-toolbox](https://github.com/googleapis/mcp-toolbox) | MCP | SQL к своему Postgres под read-only ролью | **попробовать** |
| 13 | [Telegram-канал Claude Code](../productivity/finds/telegram-channel.md) | плагин-канал | владелец пишет в Telegram — Claude на маке делает | **попробовать** |
| 14 | [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) | MCP | справка по 3 143 нодам; телеметрия по умолчанию — отключать | **попробовать**, если официального не хватит |
| 15 | [knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | плагины (официальные) | процессы sales/finance/support; коннекторы западные, ~9 тыс. токенов | позже (источник приёмов) |
| 16 | [Metabase MCP](https://github.com/metabase/metabase) | MCP (официальный) | BI поверх Postgres | позже |
| 17 | [mcp-yandex-direct](https://github.com/askads/mcp-yandex-direct) | MCP | Директ; может тратить бюджет, телеметрия — `ASKADS_TELEMETRY=0` | позже (только песочница) |
| 18 | [MAX: max-agents-skill + maxapi](https://github.com/max-messenger) | навык + SDK | бот в MAX | позже (если появится спрос) |
| — | Chatwoot, Paperless-ngx | приложения | поддержка клиентов; архив документов с OCR | позже |

**Отклонено:**
- **Zapier, Make (и их MCP), n8n Cloud** — оплата из России заблокирована,
  данные за рубежом; n8n на своём сервере их заменяет.
- **HubSpot MCP** — ушёл из России, дублирует Bitrix24. **Google Analytics
  MCP** — в России стандарт Метрика. **Odoo MCP** — редкость в малом бизнесе РФ.
- **czlonkowski/n8n-skills как есть** — по умолчанию подключён к хостингу автора.
- **ozon/wb-mcp-server (DeviceIngineering)** — запись не ограничена, веб-панель без защиты.
- **theYahia (WWmcp и 77 пакетов)** — похоже на массовую генерацию; денежные
  операции подтверждаются только на клиенте — каталог идей, не для установки.
- **MCP для amoCRM** — почти нет сообщества, запись не ограничена.
- **Telegram MCP через личный аккаунт (MTProto)** — полный доступ к аккаунту, риск бана.
- **Платные мосты** к Bitrix24 и МойСкладу — посредник видит всю CRM.
- **Activepieces, Windmill** — дублируют n8n (Activepieces — если лицензия
  n8n начнёт мешать при работе на клиентов).

## Источники

[n8n](https://github.com/n8n-io/n8n) · [n8n-io/skills](https://github.com/n8n-io/skills) ·
[n8n-mcp](https://github.com/czlonkowski/n8n-mcp) ·
[small-business-ru](https://github.com/ilyautov/small-business-ru) ·
[marketplaces-mcp-ru](https://github.com/ilyautov/marketplaces-mcp-ru) ·
[1c-odata-mcp](https://github.com/evilbruce666/1c-odata-mcp) ·
[aiogram](https://github.com/aiogram/aiogram) ·
[yandex-metrica-mcp](https://github.com/BoxLab-Ltd/yandex-metrica-mcp) ·
[mcp-toolbox](https://github.com/googleapis/mcp-toolbox) ·
[MCP Registry](https://registry.modelcontextprotocol.io/v0/servers) ·
[knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)
