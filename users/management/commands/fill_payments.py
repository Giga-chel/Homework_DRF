from django.core.management.base import BaseCommand
from users.models import User, Payment
from lms.models import Course, Lesson
from datetime import datetime


class Command(BaseCommand):
    help = 'Заполняет таблицу платежей тестовыми данными'

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            email='test@example.com',
            defaults={'password': '12345'}
        )

        course, _ = Course.objects.get_or_create(
            name='Тестовый курс',
            defaults={'description': 'Описание тестового курса'}
        )

        lesson, _ = Lesson.objects.get_or_create(
            name='Тестовый урок',
            defaults={'course': course, 'description': 'Описание тестового урока'}
        )

        Payment.objects.filter(user=user).delete()

        Payment.objects.create(
            user=user,
            paid_course=course,
            payment_amount=15000.00,
            payment_method='transfer'
        )
        Payment.objects.create(
            user=user,
            paid_lesson=lesson,
            payment_amount=1000.00,
            payment_method='cash'
        )

        self.stdout.write(self.style.SUCCESS('Успешно создано 2 тестовых платежа'))
