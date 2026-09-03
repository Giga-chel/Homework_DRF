from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, generics
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated


from users.permissions import IsUserProfileOwner
from .models import Payment, User
from .serializers import (
    PaymentSerializer,
    UserPublicSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD пользователей. create — регистрация (без токена)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ('update', 'partial_update', 'destroy'):
            # редактировать и удалять профиль может только его владелец
            return [IsAuthenticated(), IsUserProfileOwner()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            # в списке — только общая информация
            return UserPublicSerializer
        if self.action == 'retrieve':
            # свой профиль — полная информация, чужой — только общая
            if self.get_object() == self.request.user:
                return UserProfileSerializer
            return UserPublicSerializer
        return UserSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = {
        'paid_course': ['exact'],
        'paid_lesson': ['exact'],
        'payment_method': ['exact'],
    }

    ordering_fields = ['payment_date']
    ordering = ['-payment_date']

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class UserProfileAPIView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
