from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from lms.serializers import SubscriptionRequestSerializer, SubscriptionResponseSerializer

from users.permissions import IsModerator, is_moderator

from .models import Course, Lesson, Subscription
from .permissions import IsOwner
from .serializers import CourseSerializer, LessonSerializer
from .paginators import CourseLessonPagination


class OwnerQuerysetMixin:
    """Модераторам отдаёт все объекты, остальным — только их собственные."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_moderator(self.request.user):
            return queryset
        return queryset.filter(owner=self.request.user)


class CourseViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]  # list / retrieve
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


class LessonListAPIView(OwnerQuerysetMixin, generics.ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CourseLessonPagination


# ListCreateAPIView обрабатывает GET (список) и POST (создание)
class LessonCreateAPIView(generics.CreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, ~IsModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# RetrieveUpdateDestroyAPIView обрабатывает GET (одна сущность), PUT/PATCH (изменение) и DELETE (удаление)
class LessonRetrieveAPIView(OwnerQuerysetMixin, generics.RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]


class LessonUpdateAPIView(OwnerQuerysetMixin, generics.UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModerator | IsOwner]


class LessonDestroyAPIView(OwnerQuerysetMixin, generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner]

class SubscriptionAPIView(APIView):
    """Переключатель подписки: подписка есть — удаляем, нет — создаём."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SubscriptionRequestSerializer,
        responses={200: SubscriptionResponseSerializer},
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
