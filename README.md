# membot

# Телеграм-бот для анализа и пересылки мемов

Этот Телеграм-бот анализирует мемы из указанных каналов и пересылает их на основе заданных критериев. Для взаимодействия с Telegram API используется библиотека Telethon.

## Особенности

- Анализирует мемы в указанных каналах Telegram.
- Пересылает мемы в целевой канал на основе коэффициента смешности и оценки вовлеченности.
- Ведет логирование каждого шага процесса анализа и пересылки.

## Инструкции по установке

### Предварительные требования

- Python 3.9 установленный локально или в Docker-окружении.
- Docker установлен, если используется контейнеризированная среда.
- Учетные данные Telegram API (api_id и api_hash) с [официального сайта Telegram API](https://my.telegram.org/auth).

### Установка

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/your-username/mem.git
   cd mem
   ```

2. Создайте файл config.json рядом с Dockerfile и заполните его данными о конфигурации:
   ```json
   {
    "api_id": "YOUR_API_ID",
    "api_hash": "YOUR_API_HASH",
    "check_period": 30,
    "string_session": "YOUR_STRING_SESSION",
    "target_channel": "TARGET_CHANNEL_USERNAME",
    "funny_coefficient": 0.8,
    "negative_reactions": ["💩", "👎", "🤮"],
    "positive_reactions": ["❤️", "👍", "🤣", "😂", "🔥", "❤️‍🔥"],
    "spreading_coefficient": 0.10,
    "involvement_coefficient": 0.75
   }
   ```
### Запуск

#### Локальная среда

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите бота:
   ```bash
   python mem.py
   ```

#### Docker
1. Соберите Docker образ:
  ```bash
   docker build -t mem .
  ```

3. Запустите контейнер:
   ```bash
   docker run -d --name mem mem
   ```

#### Логи бота будут выводиться в STDOUT контейнера Docker или в консоль локальной среды. Вы можете просматривать их с помощью:
   ```bash
   docker logs telegram-bot
   ```
