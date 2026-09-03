from rest_framework import serializers

from .models import Course, Lesson, Subscription
from .validators import YouTubeLinkValidator


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        extra_kwargs = {'owner': {'read_only': True}}
        validators = [YouTubeLinkValidator(field='video_url')]


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = '__all__'
        extra_kwargs = {
            'owner': {'read_only': True},
        }

    def get_lessons_count(self, obj):
        return obj.lessons.count()
