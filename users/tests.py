from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from lms.models import Course
from users.models import Payment, User


class AuthTests(APITestCase):
    """Регистрация и JWT-авторизация."""

    def setUp(self):
        self.user = User.objects.create_user(email='me@example.com', password='12345qwe')

    def test_registration_available_without_token(self):
        response = self.client.post(
            reverse('users-list'),
            {'email': 'new@example.com', 'password': '12345qwe'},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
        self.assertNotIn('password', response.data)

    def test_registration_password_is_hashed(self):
        self.client.post(reverse('users-list'), {'email': 'new@example.com', 'password': '12345qwe'})

        user = User.objects.get(email='new@example.com')

        self.assertNotEqual(user.password, '12345qwe')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))

    def test_token_obtain_and_refresh(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'me@example.com', 'password': '12345qwe'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        refreshed = self.client.post(
            reverse('token_refresh'), {'refresh': response.data['refresh']}
        )

        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn('access', refreshed.data)

    def test_token_wrong_password(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'me@example.com', 'password': 'wrongpassword'},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserViewSetTests(APITestCase):
    """CRUD пользователей и ограничения профилей."""

    def setUp(self):
        self.user = User.objects.create_user(email='me@example.com', password='12345qwe')
        self.other = User.objects.create_user(email='other@example.com', password='12345qwe')

    def test_list_returns_only_public_info(self):
        """Список пользователей — только общая информация, без пароля, фамилии и платежей."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('users-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data:
            self.assertNotIn('password', item)
            self.assertNotIn('last_name', item)
            self.assertNotIn('payments', item)

    def test_own_profile_shows_payments(self):
        """Свой профиль — полная информация, включая историю платежей."""
        course = Course.objects.create(name='Курс', owner=self.user)
        Payment.objects.create(
            user=self.user, paid_course=course, payment_amount='150.00', payment_method='cash'
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('users-detail', kwargs={'pk': self.user.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payments', response.data)
        self.assertEqual(len(response.data['payments']), 1)

    def test_other_profile_hides_private_fields(self):
        """Чужой профиль — только общая информация."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('users-detail', kwargs={'pk': self.other.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('payments', response.data)
        self.assertNotIn('last_name', response.data)

    def test_can_update_own_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse('users-detail', kwargs={'pk': self.user.pk}), {'first_name': 'Иван'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Иван')

    def test_cannot_update_other_profile(self):
        """Редактирование чужого профиля запрещено."""
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse('users-detail', kwargs={'pk': self.other.pk}), {'first_name': 'Взломано'}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_delete_other_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(reverse('users-detail', kwargs={'pk': self.other.pk}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class PaymentAPITests(APITestCase):
    """Платежи: авторизация, только свои записи, фильтр и сортировка."""

    def setUp(self):
        self.user = User.objects.create_user(email='me@example.com', password='12345qwe')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='12345qwe')
        self.course = Course.objects.create(name='Курс', owner=self.user)
        self.payment = Payment.objects.create(
            user=self.user, paid_course=self.course,
            payment_amount='15000.00', payment_method='transfer',
        )
        Payment.objects.create(
            user=self.stranger, paid_course=self.course,
            payment_amount='1000.00', payment_method='cash',
        )

    def test_anonymous_gets_401(self):
        response = self.client.get(reverse('payments-list'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_sees_only_own_payments(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('payments-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user'], self.user.pk)

    def test_filter_by_payment_method(self):
        Payment.objects.create(
            user=self.user, paid_course=self.course,
            payment_amount='500.00', payment_method='cash',
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('payments-list'), {'payment_method': 'cash'})

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['payment_method'], 'cash')

    def test_ordering_desc_by_payment_date(self):
        older = Payment.objects.create(
            user=self.user, paid_course=self.course,
            payment_amount='200.00', payment_method='cash',
        )

        Payment.objects.filter(pk=older.pk).update(
            payment_date=timezone.now() - timedelta(days=1)
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('payments-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], self.payment.pk)
        self.assertEqual(response.data[1]['id'], older.pk)


class ProfileAPITests(APITestCase):
    """Эндпоинт /api/profile/ — собственный полный профиль."""

    def setUp(self):
        self.user = User.objects.create_user(email='me@example.com', password='12345qwe')

    def test_anonymous_gets_401(self):
        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_own_data_with_payments(self):
        course = Course.objects.create(name='Курс', owner=self.user)
        Payment.objects.create(
            user=self.user, paid_course=course,
            payment_amount='100.00', payment_method='cash',
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(len(response.data['payments']), 1)
