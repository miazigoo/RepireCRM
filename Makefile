SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose -f docker-compose.dev.yml
BACKEND ?= backend
FRONTEND ?= frontend
export POSTGRES_PORT ?= 55432
export REDIS_PORT ?= 56380
export BACKEND_PORT ?= 8030
export FRONTEND_PORT ?= 4200
BACKEND_URL ?= http://127.0.0.1:8030/api
FRONTEND_URL ?= http://127.0.0.1:4200
TEST_USER ?= b00bs
TEST_PASSWORD ?= QwsAzx@2000
MOCK_MONTHS ?= 12
MOCK_ORDERS ?= 720
MOCK_CUSTOMERS ?= 240
NODE_PATH_BIN ?= $(shell node -e "process.stdout.write(require('path').dirname(process.execPath))" 2>/dev/null || dirname $(shell command -v node 2>/dev/null || echo /usr/bin/node))
ANGULAR_BUILD_DIR ?= /tmp/repaircrm-angular-build

.PHONY: help up rebuild down restart ps logs logs-backend logs-frontend migrate makemigrations shell dbshell npm install \
	tests backend-tests frontend-tests lint backend-lint build smoke client-sync mock mock-small reset-mock superuser clean

help: ## Показать команды Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nRepair CRM commands:\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  make %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Запустить dev-стенд в Docker
	$(COMPOSE) up -d

rebuild: ## Пересобрать и запустить dev-стенд
	$(COMPOSE) up -d --build

down: ## Остановить dev-стенд
	$(COMPOSE) down

restart: ## Перезапустить dev-стенд
	$(COMPOSE) restart

ps: ## Показать контейнеры
	$(COMPOSE) ps

logs: ## Логи всех контейнеров
	$(COMPOSE) logs -f --tail=200

logs-backend: ## Логи backend
	$(COMPOSE) logs -f --tail=200 $(BACKEND)

logs-frontend: ## Логи frontend
	$(COMPOSE) logs -f --tail=200 $(FRONTEND)

migrate: ## Применить миграции backend
	$(COMPOSE) exec -T $(BACKEND) python manage.py migrate

makemigrations: ## Создать миграции backend
	$(COMPOSE) exec -T $(BACKEND) python manage.py makemigrations

shell: ## Django shell внутри backend-контейнера
	$(COMPOSE) exec $(BACKEND) python manage.py shell

dbshell: ## Django dbshell внутри backend-контейнера
	$(COMPOSE) exec $(BACKEND) python manage.py dbshell

npm: ## npm-команда во frontend-контейнере, пример: make npm CMD="install"
	$(COMPOSE) exec -T $(FRONTEND) npm $(CMD)

install: ## Установить frontend-зависимости в контейнере
	$(COMPOSE) exec -T $(FRONTEND) npm ci

tests: backend-tests frontend-tests lint build ## Backend + frontend tests, lint и build

backend-tests: ## Backend tests в изолированной sqlite БД внутри контейнера
	$(COMPOSE) exec -T $(BACKEND) sh -lc 'DATABASE_URL=sqlite:////tmp/repaircrm_backend_tests.sqlite3 python manage.py test tests'

frontend-tests: ## Frontend unit tests в ChromeHeadlessNoSandbox
	$(COMPOSE) exec -T $(FRONTEND) npm run test:ci

lint: backend-lint ## Все доступные линтеры

backend-lint: ## Backend flake8
	$(COMPOSE) exec -T $(BACKEND) flake8 --config=.flake8

build: ## Angular build без записи в root-owned dist
	cd frontend/crm-app && PATH="$(NODE_PATH_BIN):$$PATH" npx ng build --output-path=$(ANGULAR_BUILD_DIR)

smoke: ## Проверить live API по запущенному стенду
	python3 scripts/api_smoke.py --base-url $(BACKEND_URL) --username $(TEST_USER) --password '$(TEST_PASSWORD)'

client-sync: ## Ручной запуск синхронизации с внешним клиентским сервисом
	$(COMPOSE) exec -T $(BACKEND) python manage.py sync_client_service

mock: up migrate ## Пересоздать большую demo-базу за год
	$(COMPOSE) exec -T $(BACKEND) python manage.py create_test_data --reset-demo --months $(MOCK_MONTHS) --orders $(MOCK_ORDERS) --customers $(MOCK_CUSTOMERS)
	@printf "\nDemo ready:\n  Frontend: %s\n  API:      %s\n  Login:    %s / %s\n" "$(FRONTEND_URL)" "$(BACKEND_URL)" "$(TEST_USER)" "$(TEST_PASSWORD)"

mock-small: up migrate ## Быстрая маленькая demo-база для проверки сидера
	$(COMPOSE) exec -T $(BACKEND) python manage.py create_test_data --reset-demo --months 3 --orders 60 --customers 30

reset-mock: up migrate ## Очистить demo-записи
	$(COMPOSE) exec -T $(BACKEND) python manage.py create_test_data --only-reset

superuser: ## Создать/обновить суперпользователя из env контейнера
	$(COMPOSE) exec -T $(BACKEND) python manage.py shell -c 'from init_superuser import run; run()'

clean: ## Остановить стенд и удалить volume'ы dev-БД
	$(COMPOSE) down -v
