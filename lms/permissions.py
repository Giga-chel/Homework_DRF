from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Допускает только владельца объекта (у объекта есть поле owner)."""

    message = 'Действие доступно только владельцу'

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
