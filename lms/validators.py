from urllib.parse import urlparse

from rest_framework.exceptions import ValidationError

# Домены YouTube, ссылки на которые разрешены в материалах.
# При желании сюда можно добавить короткий домен 'youtu.be'.
ALLOWED_VIDEO_HOSTS = ('youtube.com', 'www.youtube.com', 'm.youtube.com')


class YouTubeLinkValidator:
    """Проверяет, что ссылка на видео ведёт только на youtube.com.

    Подключается в сериализаторе как объектный валидатор:

        class Meta:
            validators = [YouTubeLinkValidator(field='video_url')]

    Пустое значение пропускается — поле video_url необязательное.
    """

    message = 'Ссылки на видео допускаются только на youtube.com.'

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        url = attrs.get(self.field)
        if not url:
            return
        host = urlparse(url).netloc.lower()
        if host not in ALLOWED_VIDEO_HOSTS:
            raise ValidationError({self.field: self.message})
