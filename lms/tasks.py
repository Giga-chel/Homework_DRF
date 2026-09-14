from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Course


@shared_task
def send_course_update_notification(course_id):
    """Рассылает письма подписчикам курса об обновлении материалов (задание 2)."""

    # в задачу передаём только id — аргументы должны сериализоваться
    course = Course.objects.filter(pk=course_id).first()
    if course is None:
        return f'Курс id={course_id} не найден, рассылка отменена'

    sent = 0
    for subscription in course.subscriptions.select_related('user'):
        send_mail(
            subject=f'Обновление курса «{course.name}»',
            message=(
                'Здравствуйте!\n\n'
                f'Материалы курса «{course.name}», на который вы подписаны, были обновлены.\n\n'
                'Чтобы отписаться от уведомлений, используйте эндпоинт подписок.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.user.email],
            fail_silently=False,
        )
        sent += 1

    return f'Курс «{course.name}»: отправлено писем — {sent}'
