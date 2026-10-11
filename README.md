
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

## Запуск локально (одна команда)
1. cp .env.template .env — заполнить SECRET_KEY и STRIPE_SECRET_KEY
2. docker compose up -d --build  (web, nginx, postgres, redis, celery, beat)
3. docker compose exec web python manage.py createsuperuser
4. http://localhost/ — приложение, /admin/ — админка
Остановка: docker compose down (данные в volumes сохраняются).

## CI/CD и деплой
- На push/PR: flake8, тесты (postgres/redis как service-контейнеры), сборка Docker-образа.
- При push в develop после успешных проверок — SSH-деплой на сервер:
  git pull → docker compose up -d --build → чистка старых образов.
- Секреты: SSH_HOST, SSH_USER, SSH_PRIVATE_KEY (Settings → Secrets → Actions).
- Сервер: Docker + Docker Compose, проект в /var/www/lms, серверный .env.
