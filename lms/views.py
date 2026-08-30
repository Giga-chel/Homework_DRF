from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

# ListCreateAPIView обрабатывает GET (список) и POST (создание)
class LessonListCreateAPIView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

# RetrieveUpdateDestroyAPIView обрабатывает GET (одна сущность), PUT/PATCH (изменение) и DELETE (удаление)
class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
