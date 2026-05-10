#!/bin/bash

echo "🚀 Настройка среды разработки Repair CRM"

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

# Проверяем наличие Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и повторите попытку."
    exit 1
fi

# Создаем .env файл
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    cat > .env << EOL
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://postgres:postgres@db:5432/repair_crm
REDIS_URL=redis://redis:6379/0
POSTGRES_DB=repair_crm
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ALLOWED_HOSTS=localhost,127.0.0.1
EOL
fi

# Устанавливаем pre-commit hooks
echo "🔧 Устанавливаем pre-commit hooks..."
pip install pre-commit
pre-commit install

# Запускаем контейнеры
echo "🐳 Запускаем Docker контейнеры..."
docker compose -f docker-compose.dev.yml up --build -d

echo "✅ Среда разработки настроена!"
echo "🌐 Frontend: http://localhost:4200"
echo "🔧 Backend API: http://localhost:8030"
echo "📊 Django Admin: http://localhost:8030/admin"
