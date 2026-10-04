from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta

from django.utils import timezone

from users.permissions import IsModerator, is_moderator

from .models import Course, Lesson, Subscription
from .tasks import send_course_update_notification
from .paginators import CourseLessonPagination
from .permissions import IsOwner
from .serializers import (
    CourseSerializer,
    LessonSerializer,
    SubscriptionRequestSerializer,
    SubscriptionResponseSerializer,
)


class OwnerQuerysetMixin:
    """Модераторам отдаёт все объекты, остальным — только их собственные."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_moderator(self.request.user):
            return queryset
        return queryset.filter(owner=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary='Список курсов',
        description='Модератору доступны все курсы, остальным — только собственные. Пагинация: ?page, ?page_size (максимум 50).',
    ),
    create=extend_schema(
        summary='Создание курса',
        description='Доступно всем авторизованным, кроме модераторов. Владелец привязывается автоматически.',
        responses={
            201: CourseSerializer,
            400: OpenApiResponse(description='Некорректные данные'),
            403: OpenApiResponse(description='Модераторам создание запрещено'),
        },
    ),
    retrieve=extend_schema(
        summary='Детали курса',
        responses={
            200: CourseSerializer,
            404: OpenApiResponse(description='Курс не найден или недоступен'),
        },
    ),
    update=extend_schema(
        summary='Полное обновление курса',
        description='Доступно модератору или владельцу.',
        responses={
            200: CourseSerializer,
            403: OpenApiResponse(description='Пользователь не модератор и не владелец'),
            404: OpenApiResponse(description='Курс не найден или недоступен'),
        },
    ),
    partial_update=extend_schema(
        summary='Частичное обновление курса',
        description='Доступно модератору или владельцу.',
        responses={
            200: CourseSerializer,
            403: OpenApiResponse(description='Пользователь не модератор и не владелец'),
            404: OpenApiResponse(description='Курс не найден или недоступен'),
        },
    ),
    destroy=extend_schema(
        summary='Удаление курса',
        description='Доступно только владельцу; модераторам удаление запрещено.',
        responses={
            204: OpenApiResponse(description='Курс удалён'),
            403: OpenApiResponse(description='Пользователь не владелец курса'),
            404: OpenApiResponse(description='Курс не найден или недоступен'),
        },
    ),
)
class CourseViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CourseLessonPagination

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAuthenticated, ~IsModerator]
        elif self.action in ('update', 'partial_update'):
            self.permission_classes = [IsAuthenticated, IsModerator | IsOwner]
        elif self.action == 'destroy':
            self.permission_classes = [IsAuthenticated, IsOwner]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if timezone.now() - serializer.instance.updated_at > timedelta(hours=4):
            send_course_update_notification.delay(serializer.instance.pk)
        serializer.save()


@extend_schema_view(
    get=extend_schema(
        summary='Список уроков',
        description='Модератору доступны все уроки, остальным — только собственные. Пагинация: ?page, ?page_size (максимум 50).',
    ),
)
class LessonListAPIView(OwnerQuerysetMixin, generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CourseLessonPagination


@extend_schema_view(
    post=extend_schema(
        summary='Создание урока',
        description='Доступно всем авторизованным, кроме модераторов. Владелец привязывается автоматически. Ссылка на видео — только youtube.com.',
        responses={
            201: LessonSerializer,
            400: OpenApiResponse(description='Некорректные данные или запрещённая ссылка на видео'),
            403: OpenApiResponse(description='Модераторам создание запрещено'),
        },
    ),
)
class LessonCreateAPIView(generics.CreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, ~IsModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary='Детали урока',
        responses={
            200: LessonSerializer,
            404: OpenApiResponse(description='Урок не найден или недоступен'),
        },
    ),
)
class LessonRetrieveAPIView(OwnerQuerysetMixin, generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    put=extend_schema(
        summary='Полное обновление урока',
        description=(
            'Доступно модератору или владельцу. Обновление урока считается обновлением курса: '
            'подписчикам уходит письмо, если курс не обновлялся более 4 часов.'
        ),
        responses={
            200: LessonSerializer,
            403: OpenApiResponse(description='Пользователь не модератор и не владелец'),
            404: OpenApiResponse(description='Урок не найден или недоступен'),
        },
    ),
    patch=extend_schema(
        summary='Частичное обновление урока',
        description=(
            'Доступно модератору или владельцу. Обновление урока считается обновлением курса: '
            'подписчикам уходит письмо, если курс не обновлялся более 4 часов.'
        ),
        responses={
            200: LessonSerializer,
            403: OpenApiResponse(description='Пользователь не модератор и не владелец'),
            404: OpenApiResponse(description='Урок не найден или недоступен'),
        },
    ),
)
class LessonUpdateAPIView(OwnerQuerysetMixin, generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModerator | IsOwner]

    def perform_update(self, serializer):
        lesson = serializer.instance
        course = lesson.course

        if timezone.now() - course.updated_at > timedelta(hours=4):
            send_course_update_notification.delay(course.pk)

        serializer.save()
        Course.objects.filter(pk=course.pk).update(updated_at=timezone.now())
class LessonDestroyAPIView(OwnerQuerysetMixin, generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner]


class SubscriptionAPIView(APIView):
    """Переключатель подписки: подписка есть — удаляем, нет — создаём."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SubscriptionRequestSerializer,
        responses={
            200: SubscriptionResponseSerializer,
            400: OpenApiResponse(description='Не указан или некорректный course_id'),
            401: OpenApiResponse(description='Требуется авторизация'),
            404: OpenApiResponse(description='Курс не найден'),
        },
        tags=['subscriptions'],
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {'error': 'Укажите course_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course_item = get_object_or_404(Course, pk=course_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Некорректный course_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subs_item = Subscription.objects.filter(user=user, course=course_item)

        if subs_item.exists():
            subs_item.delete()
            message = 'подписка удалена'
        else:
            Subscription.objects.create(user=user, course=course_item)
            message = 'подписка добавлена'

        return Response({'message': message})
