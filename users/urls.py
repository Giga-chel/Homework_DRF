from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    PaymentCreateAPIView,
    PaymentStatusAPIView,
    PaymentViewSet,
    UserProfileAPIView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    # ВАЖНО: payments/create/ идёт ПЕРЕД include(router.urls) —
    # иначе POST перехватит детальный маршрут роутера payments/<pk>/ и вернёт 405
    path('payments/create/', PaymentCreateAPIView.as_view(), name='payment-create'),
    path('payments/status/<str:session_id>/', PaymentStatusAPIView.as_view(), name='payment-status'),
    path('', include(router.urls)),
    # JWT: получение пары токенов и обновление access-токена
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
]
