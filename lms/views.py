from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsModerator, is_moderator

from .models import Course, Lesson
from .permissions import IsOwner
from .serializers import CourseSerializer, LessonSerializer


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
