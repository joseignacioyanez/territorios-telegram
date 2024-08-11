# Dockerfile for Telegram Bot
FROM python:3.10.14-alpine3.20

WORKDIR /bot

COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /bot/

CMD ["python", "./scripts/telegram_bot.py"]
