import stripe
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, generics
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from lms.models import Course
from users.permissions import IsUserProfileOwner
from . import services
from .models import Payment, User
from .serializers import (
    PaymentCreateRequestSerializer,
    PaymentSerializer,
    PaymentStatusSerializer,
    UserProfileSerializer,
    UserPublicSerializer,
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


class PaymentCreateAPIView(APIView):
    """Создание платежа: продукт + цена + сессия в Stripe, в ответе — ссылка на оплату."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PaymentCreateRequestSerializer,
        responses={201: PaymentSerializer},
        tags=['payments'],
    )
    def post(self, request, *args, **kwargs):
        serializer = PaymentCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_id = serializer.validated_data['course_id']

        course = get_object_or_404(Course, pk=course_id)
        if not course.price or course.price <= 0:
            return Response(
                {'error': 'У курса не задана цена'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = services.create_product(course.name)
            price = services.create_price(product.id, course.price)
            session = services.create_checkout_session(price.id)
        except stripe.StripeError as exc:
            return Response(
                {'error': f'Ошибка платёжного сервиса Stripe: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment = Payment.objects.create(
            user=request.user,
            paid_course=course,
            payment_amount=course.price,
            payment_method='transfer',
            session_id=session.id,
            payment_link=session.url,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentStatusAPIView(APIView):
    """Доп. задание: статус платежа в Stripe по id сессии."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PaymentStatusSerializer, tags=['payments'])
    def get(self, request, session_id, *args, **kwargs):
        # статус отдаём только по собственным платежам
        get_object_or_404(Payment, session_id=session_id, user=request.user)
        try:
            session = services.retrieve_session(session_id)
        except stripe.StripeError as exc:
            return Response(
                {'error': f'Ошибка платёжного сервиса Stripe: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({
            'session_id': session.id,
            'payment_status': session.payment_status,
            'status': session.status,
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Платежи только для чтения: создание — через /payments/create/ (Stripe)."""

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
