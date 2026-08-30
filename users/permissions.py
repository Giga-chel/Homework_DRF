from rest_framework.permissions import BasePermission

MODERATORS_GROUP_NAME = 'moderators'


def is_moderator(user):
    """Проверяет, входит ли пользователь в группу модераторов."""
    return (
        user.is_authenticated
        and user.groups.filter(name=MODERATORS_GROUP_NAME).exists()
    )


class IsModerator(BasePermission):
    """Допускает только пользователей из группы модераторов."""

    message = 'Доступ разрешён только модераторам'

    def has_permission(self, request, view):
        return is_moderator(request.user)

    def has_object_permission(self, request, view, obj):
        return is_moderator(request.user)
