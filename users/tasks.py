from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@shared_task
def deactivate_inactive_users():
    """Блокирует (is_active=False) пользователей, не заходивших более месяца (задание 3).

    last_login IS NULL (пользователь ни разу не входил) фильтром не затрагивается —
    по такому пользователю нет данных для решения. Суперпользователей не блокируем,
    чтобы не потерять доступ к админке.
    """
    month_ago = timezone.now() - timedelta(days=30)

    blocked = User.objects.filter(
        is_active=True,
        is_superuser=False,
        last_login__lt=month_ago,
    ).update(is_active=False)

    return f'Заблокировано пользователей: {blocked}'