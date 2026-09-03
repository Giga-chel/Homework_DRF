from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class UserViewSetTests(APITestCase):
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
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('users-detail', kwargs={'pk': self.user.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payments', response.data)

    def test_other_profile_hides_private_fields(self):
        """Чужой профиль — только общая информация."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('users-detail', kwargs={'pk': self.other.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('payments', response.data)
        self.assertNotIn('last_name', response.data)

    def test_cannot_update_other_profile(self):
        """Редактирование чужого профиля запрещено."""
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse('users-detail', kwargs={'pk': self.other.pk}),
            {'first_name': 'Взломано'},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
