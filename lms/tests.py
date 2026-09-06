from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from lms.models import Course, Lesson, Subscription
from users.models import User


class LmsBaseTestCase(APITestCase):
    """Общие данные для тестов LMS."""

    def setUp(self):
        self.moderators_group = Group.objects.create(name='moderators')

        self.owner = User.objects.create_user(email='owner@example.com', password='12345qwe')
        self.moderator = User.objects.create_user(email='moder@example.com', password='12345qwe')
        self.moderator.groups.add(self.moderators_group)
        self.stranger = User.objects.create_user(email='stranger@example.com', password='12345qwe')

        self.course = Course.objects.create(name='Тестовый курс', owner=self.owner)
        self.lesson = Lesson.objects.create(
            course=self.course,
            name='Тестовый урок',
            owner=self.owner,
        )


class LessonCRUDTests(LmsBaseTestCase):
    """CRUD уроков для пользователей с разными правами."""

    # ---------- аноним ----------

    def test_anonymous_cannot_list_lessons(self):
        response = self.client.get(reverse('lesson-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_create_lesson(self):
        response = self.client.post(
            reverse('lesson-create'), {'course': self.course.pk, 'name': 'Урок'}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---------- владелец ----------

        def test_owner_can_create_lesson_and_becomes_owner(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.post(
                reverse('lesson-create'),
                {'course': self.course.pk, 'name': 'Новый урок'},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            # урок автоматически привязывается к создателю
            self.assertEqual(response.data['owner'], self.owner.pk)

        def test_user_sees_only_own_lessons(self):
            Lesson.objects.create(course=self.course, name='Чужой урок', owner=self.stranger)
            self.client.force_authenticate(user=self.stranger)
            response = self.client.get(reverse('lesson-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 1)
            self.assertEqual(response.data['results'][0]['owner'], self.stranger.pk)

        def test_owner_can_retrieve_own_lesson(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.get(reverse('lesson-detail', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_owner_can_update_own_lesson(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.patch(
                reverse('lesson-update', kwargs={'pk': self.lesson.pk}),
                {'name': 'Обновлённый урок'},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.lesson.refresh_from_db()
            self.assertEqual(self.lesson.name, 'Обновлённый урок')

        def test_owner_can_delete_own_lesson(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.delete(reverse('lesson-delete', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # ---------- посторонний пользователь ----------

        def test_stranger_cannot_retrieve_others_lesson(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.get(reverse('lesson-detail', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        def test_stranger_cannot_update_others_lesson(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.patch(
                reverse('lesson-update', kwargs={'pk': self.lesson.pk}), {'name': 'Взлом'}
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        def test_stranger_cannot_delete_others_lesson(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.delete(reverse('lesson-delete', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # ---------- модератор ----------

        def test_moderator_can_retrieve_any_lesson(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.get(reverse('lesson-detail', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_moderator_can_update_any_lesson(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.patch(
                reverse('lesson-update', kwargs={'pk': self.lesson.pk}),
                {'name': 'Правка модератора'},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_moderator_cannot_create_lesson(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.post(
                reverse('lesson-create'),
                {'course': self.course.pk, 'name': 'Урок модератора'},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def test_moderator_cannot_delete_lesson(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.delete(reverse('lesson-delete', kwargs={'pk': self.lesson.pk}))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    class LessonVideoUrlValidatorTests(APITestCase):
        """Валидатор ссылок на видео (задание 1)."""

        def setUp(self):
            self.user = User.objects.create_user(email='owner@example.com', password='12345qwe')
            self.course = Course.objects.create(name='Курс', owner=self.user)

        def _create_lesson(self, data):
            self.client.force_authenticate(user=self.user)
            return self.client.post(reverse('lesson-create'), data)

        def test_youtube_link_is_accepted(self):
            response = self._create_lesson({
                'course': self.course.pk,
                'name': 'Урок',
                'video_url': 'https://www.youtube.com/watch?v=abc123',
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        def test_foreign_link_is_rejected(self):
            response = self._create_lesson({
                'course': self.course.pk,
                'name': 'Урок',
                'video_url': 'https://vimeo.com/12345',
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('video_url', response.data)

        def test_fake_domain_is_rejected(self):
            # подделка домена: youtube.com внутри имени чужого хоста
            response = self._create_lesson({
                'course': self.course.pk,
                'name': 'Урок',
                'video_url': 'https://youtube.com.evil.ru/watch',
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        def test_empty_video_url_is_allowed(self):
            response = self._create_lesson({'course': self.course.pk, 'name': 'Урок'})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    class SubscriptionTests(APITestCase):
        """Подписка на обновления курса (задание 2)."""

        def setUp(self):
            self.user = User.objects.create_user(email='user@example.com', password='12345qwe')
            self.course = Course.objects.create(name='Курс', owner=self.user)

        def test_anonymous_cannot_subscribe(self):
            response = self.client.post(reverse('subscription-toggle'), {'course_id': self.course.pk})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        def test_first_post_adds_subscription(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.post(reverse('subscription-toggle'), {'course_id': self.course.pk})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['message'], 'подписка добавлена')
            self.assertTrue(
                Subscription.objects.filter(user=self.user, course=self.course).exists()
            )

        def test_second_post_removes_subscription(self):
            self.client.force_authenticate(user=self.user)
            self.client.post(reverse('subscription-toggle'), {'course_id': self.course.pk})
            response = self.client.post(reverse('subscription-toggle'), {'course_id': self.course.pk})
            self.assertEqual(response.data['message'], 'подписка удалена')
            self.assertFalse(
                Subscription.objects.filter(user=self.user, course=self.course).exists()
            )

        def test_course_detail_shows_subscription_flag(self):
            self.client.force_authenticate(user=self.user)
            Subscription.objects.create(user=self.user, course=self.course)
            response = self.client.get(reverse('courses-detail', kwargs={'pk': self.course.pk}))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['is_subscribed'])

        def test_course_detail_flag_false_without_subscription(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(reverse('courses-detail', kwargs={'pk': self.course.pk}))
            self.assertFalse(response.data['is_subscribed'])

        def test_nonexistent_course_returns_404(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.post(reverse('subscription-toggle'), {'course_id': 999})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        def test_missing_course_id_returns_400(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.post(reverse('subscription-toggle'), {})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        def test_non_numeric_course_id_returns_400(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.post(reverse('subscription-toggle'), {'course_id': 'abc'})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    class PaginationTests(APITestCase):
        """Пагинация списков (задание 3)."""

        def setUp(self):
            self.user = User.objects.create_user(email='pager@example.com', password='12345qwe')
            self.course = Course.objects.create(name='Курс', owner=self.user)
            Lesson.objects.bulk_create([
                Lesson(course=self.course, name=f'Урок {i}', owner=self.user)
                for i in range(60)
            ])

        def test_lessons_paginated_by_default(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(reverse('lesson-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('count', response.data)
            self.assertIn('results', response.data)
            self.assertEqual(response.data['count'], 60)
            self.assertEqual(len(response.data['results']), 10)  # page_size
            self.assertIsNotNone(response.data['next'])

        def test_page_size_query_param(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(reverse('lesson-list'), {'page_size': 7})
            self.assertEqual(len(response.data['results']), 7)

        def test_page_size_capped_by_max(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(reverse('lesson-list'), {'page_size': 1000})
            self.assertEqual(len(response.data['results']), 50)  # max_page_size

        def test_courses_paginated(self):
            self.client.force_authenticate(user=self.user)
            response = self.client.get(reverse('courses-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('results', response.data)
            self.assertEqual(len(response.data['results']), 1)

    class CourseCRUDTests(LmsBaseTestCase):
        """CRUD курсов для разных прав (покрывает оставшиеся эндпоинты lms)."""

        def test_user_can_create_course_and_becomes_owner(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.post(reverse('courses-list'), {'name': 'Новый курс'})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['owner'], self.stranger.pk)

        def test_owner_can_update_own_course(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.patch(
                reverse('courses-detail', kwargs={'pk': self.course.pk}), {'name': 'Новое имя'}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_owner_can_delete_own_course(self):
            self.client.force_authenticate(user=self.owner)
            response = self.client.delete(reverse('courses-detail', kwargs={'pk': self.course.pk}))
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        def test_stranger_sees_no_foreign_courses(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.get(reverse('courses-list'))
            self.assertEqual(response.data['count'], 0)

        def test_stranger_cannot_delete_others_course(self):
            self.client.force_authenticate(user=self.stranger)
            response = self.client.delete(reverse('courses-detail', kwargs={'pk': self.course.pk}))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        def test_moderator_can_update_any_course(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.patch(
                reverse('courses-detail', kwargs={'pk': self.course.pk}), {'name': 'Правка'}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def test_moderator_cannot_create_course(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.post(reverse('courses-list'), {'name': 'Курс модератора'})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        def test_moderator_cannot_delete_course(self):
            self.client.force_authenticate(user=self.moderator)
            response = self.client.delete(reverse('courses-detail', kwargs={'pk': self.course.pk}))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)