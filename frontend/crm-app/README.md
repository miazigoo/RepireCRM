# Frontend Repair CRM

Angular-приложение Repair CRM. Основная документация проекта, команды запуска,
скриншоты и описание архитектуры находятся в корневом [README.md](../../README.md).

## Локальная разработка

Обычно frontend запускается через Docker Compose из корня проекта:

```bash
make up
```

Адрес dev-стенда:

```text
http://127.0.0.1:4200
```

## Команды внутри frontend

```bash
npm run start:dev   # Angular dev server с dev proxy
npm run build       # production build
npm run test:ci     # unit tests в ChromeHeadlessNoSandbox
```

Через Makefile из корня:

```bash
make frontend-tests
make build
make npm CMD="install <package>"
```

## Стек

- Angular 20
- Angular Material
- RxJS
- NgRx
- SCSS/CSS variables для тем
- Karma + ChromeHeadless для unit-тестов
