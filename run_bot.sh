#!/bin/bash

# Скрипт для запуска Annoying Bot

echo "🤖 Запуск Annoying Bot..."

# Проверяем, существует ли виртуальное окружение
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте виртуальное окружение: python3 -m venv venv"
    exit 1
fi

# Проверяем, существует ли файл .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env на основе env_example.txt"
    exit 1
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Проверяем, установлены ли зависимости
if ! python -c "import telegram" 2>/dev/null; then
    echo "📦 Установка зависимостей..."
    pip install -r requirements.txt
fi

# Запускаем бота
echo "🚀 Запуск бота..."
python bot.py 