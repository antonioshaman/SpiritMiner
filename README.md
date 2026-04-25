# SpiritMiner

**Telegram-бот для раннего обнаружения PoW-монет**

[@SpiritMiner_bot](https://t.me/SpiritMiner_bot) — находит новые PoW-монеты раньше толпы. Считает скоринг, оценивает риск, показывает окно входа и момент выхода.

Не *"что выгодно сейчас"* — а **"что станет выгодным через 12-72 часа"**.

## Возможности

| Функция | Описание |
|---------|----------|
| Новые PoW-монеты | Свежие находки с WhatToMine API |
| Топ по скорингу | Рейтинг 100 баллов (8 критериев + 4 штрафа) |
| Проверить монету | Полный анализ: цена, сложность, пулы, GitHub, соцсети |
| Рассчитать вход | Стратегия входа с рекомендациями по объёму |
| Условия выхода | Сигналы выхода: сложность x3/x5, цена vs сложность |
| Калькулятор железа | PnL для 6 GPU (RTX 4090, 4070 Ti, 3080, 3060 Ti, RX 7900 XTX, 6800 XT) |
| Провайдер-чекер | Где можно майнить: Hetzner, Vast.ai, NiceHash и др. |
| Spirit Points | Геймификация: очки за активность, 5 уровней |
| Spirit Rank | Рейтинг разведчиков + лидерборд |
| Голосование | Sentiment index: bullish/watching/bearish |
| Партнёры | Пулы и биржи для майнинга и продажи |
| Spirit Index | Агрегированный пульс рынка 0-100 |
| Алерты | Push-уведомления о новых сигналах и выходах |

## Скоринг (100 баллов)

| Критерий | Баллы |
|----------|-------|
| Возраст < 7 дней | +20 |
| Рабочий explorer | +15 |
| 2+ пула | +15 |
| GitHub с коммитами | +15 |
| Активное комьюнити | +10 |
| Листинг на бирже | +10 |
| Низкая сложность | +10 |
| Токеномика | +5 |

**Штрафы:** премайн (-20), нет explorer (-20), нет ликвидности (-30), анон-форк (-40)

**Сигналы:** 60+ = можно пробовать | 35-59 = только тестовым объёмом | <35 = не лезть

## Стек

- Python 3.12 + aiogram 3.x
- aiosqlite (async SQLite)
- APScheduler
- aiohttp + BeautifulSoup4

## Источники данных

- [WhatToMine](https://whattomine.com) API — монеты, алгоритмы, профитабельность
- [CoinGecko](https://www.coingecko.com) API — рынок, биржи, комьюнити, genesis date
- [GitHub](https://github.com) API — активность разработки
- [MiningPoolStats](https://miningpoolstats.stream) — пулы (HTML scraping)

## Установка

```bash
git clone git@github.com:antonioshaman/SpiritMiner.git
cd SpiritMiner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Конфигурация

Переменные окружения:

| Переменная | Описание |
|-----------|----------|
| `SPIRITMINER_BOT_TOKEN` | Telegram Bot API токен |
| `WTM_API_KEY` | WhatToMine API ключ |

## Запуск

```bash
export SPIRITMINER_BOT_TOKEN="your-token"
export WTM_API_KEY="your-key"
python bot.py
```

### systemd

```ini
[Unit]
Description=SpiritMiner PoW Coin Detection Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/SpiritMiner
Environment=SPIRITMINER_BOT_TOKEN=your-token
Environment=WTM_API_KEY=your-key
ExecStart=/path/to/SpiritMiner/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Деплой

```bash
./deploy.sh  # bump version, push, install deps, restart service
```

## Spirit Points

| Действие | Очки |
|----------|------|
| Поиск монеты | +1 SP |
| Голосование | +2 SP |
| Скоринг | +2 SP |
| Вход в монету | +5 SP |
| Выход из монеты | +5 SP |
| Бонус ROI > 20% | +10 SP |

**Уровни:** Новичок (0) — Разведчик (50) — Охотник (200) — Мастер (500) — Легенда (1000)

## Лицензия

MIT

## Поддержка

Если бот полезен — можно поддержать автора:

**Telegram:** [@shamanael](https://t.me/shamanael)
