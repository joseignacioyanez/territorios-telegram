# Dockerfile for Telegram Bot
FROM python:3.10.14-slim-bullseye

# Install locale package and generate locale
RUN apt-get update && \
    apt-get install -y locales && \
    locale-gen es_ES.UTF-8

# Set locale environment variables
ENV LANG=es_ES.UTF-8
ENV LC_ALL=es_ES.UTF-8

WORKDIR /bot

COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /bot/

CMD ["python", "./scripts/telegram_bot.py"]
