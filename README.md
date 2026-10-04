
# Homework DRF — учебная платформа (LMS) v2

REST API учебной платформы: курсы, уроки, подписки, платежи (Stripe), пользователи.
Документация API — Swagger UI (drf-spectacular).

## Стек
Python 3.14, Django, Django REST Framework, SimpleJWT, django-filter,
PostgreSQL, Redis, Celery (воркер + beat), Docker Compose.

## Запуск через Docker

1. Клонируйте репозиторий:
   git clone https://github.com/Giga-chel/Homework_DRF.git
   cd Homework_DRF
2. Создайте файл `.env` из примера и заполните значения:
   cp .env.example .env
   (обязательно: SECRET_KEY, STRIPE_SECRET_KEY)
3. Запустите все сервисы (миграции выполняются автоматически):
   docker compose up -d --build
4. Создайте суперпользователя:
   docker compose exec web python manage.py createsuperuser
5. Приложение — http://localhost:8000/, админка — http://localhost:8000/admin/

## Сервисы

| Сервис     | Назначение                                  | Доступ                     |
|------------|---------------------------------------------|----------------------------|
| web        | Django-приложение                           | http://localhost:8000      |
| db         | PostgreSQL 16                               | только внутри сети compose |
| redis      | Redis 7 (брокер Celery)                     | только внутри сети compose |
| celery     | фоновые задачи                              | только внутри сети compose |
| celery-beat| периодические задачи                        | только внутри сети compose |

Данные PostgreSQL и Redis хранятся в volumes (`pg_data`, `redis_data`)
и сохраняются при перезапуске контейнеров.

## Полезные команды

* docker compose logs -f web          # логи приложения
* docker compose logs -f celery       # логи воркера
* docker compose exec web python manage.py shell
* docker compose down                 # остановка, данные сохранятся
* docker compose down -v              # остановка с удалением данных

## Локальный запуск без Docker (Poetry)

1. poetry install
2. Требуются локально запущенные PostgreSQL и Redis. Переменные DB_HOST=localhost
и CELERY_BROKER_URL=redis://localhost:6379/0 задайте в Run Configuration
3. PyCharm — переменные окружения имеют приоритет над .env.
4. poetry run python manage.py migrate
5. poetry run python manage.py runserver

## Деплой (CI/CD)

Приложение развёрнуто на VPS (Ubuntu 24.04): Nginx (:80) → Gunicorn → Django,
PostgreSQL и Redis на localhost, Celery worker + beat — systemd с авточперезапуском.

Пайплайн `.github/workflows/ci_cd.yml`:
1. Тесты (flake8 + Django-тесты с PostgreSQL/Redis) — на каждый push и PR;
2. Деплой на сервер по SSH после успешных тестов при push в main:
   git pull → зависимости → миграции → collectstatic → рестарт сервисов.

Секреты (Settings → Secrets and variables → Actions):
SSH_HOST, SSH_USER, SSH_PRIVATE_KEY.
