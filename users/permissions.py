from rest_framework.permissions import BasePermission, SAFE_METHODS

MODERATORS_GROUP_NAME = 'moderators'


def is_moderator(user):
    return (
        user.is_authenticated
        and user.groups.filter(name=MODERATORS_GROUP_NAME).exists()
    )


class IsModerator(BasePermission):
    message = 'Доступ разрешён только модераторам'

    def has_permission(self, request, view):
        return is_moderator(request.user)

    def has_object_permission(self, request, view, obj):
        return is_moderator(request.user)


class IsUserProfileOwner(BasePermission):
    """Просмотр профиля — всем авторизованным, изменение — только самому пользователю."""

    message = 'Редактировать профиль может только его владелец'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user
