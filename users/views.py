import stripe
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
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
    UserPublicSerializer,
    UserProfileSerializer,
    UserSerializer,
)


@extend_schema_view(
    create=extend_schema(
        auth=[],
        summary='Регистрация пользователя',
        description='Доступна без авторизации. Пароль хешируется и в ответе не возвращается.',
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description='Некорректные данные (email занят, пропущены поля)'),
        },
    ),
    list=extend_schema(
        summary='Список пользователей (общая информация)',
        responses={
            200: UserPublicSerializer(many=True),
            401: OpenApiResponse(description='Требуется авторизация'),
        },
    ),
    retrieve=extend_schema(
        summary='Профиль пользователя',
        description=(
            'Для чужого профиля — только общая информация. '
            'Свой профиль возвращается в полном виде (фамилия, история платежей).'
        ),
        responses={
            200: UserPublicSerializer,
            401: OpenApiResponse(description='Требуется авторизация'),
            404: OpenApiResponse(description='Пользователь не найден'),
        },
    ),
    update=extend_schema(
        summary='Полное обновление своего профиля',
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description='Требуется авторизация'),
            403: OpenApiResponse(description='Редактировать можно только свой профиль'),
        },
    ),
    partial_update=extend_schema(
        summary='Частичное обновление своего профиля',
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description='Требуется авторизация'),
            403: OpenApiResponse(description='Редактировать можно только свой профиль'),
        },
    ),
    destroy=extend_schema(
        summary='Удаление своего профиля',
        responses={
            204: OpenApiResponse(description='Профиль удалён'),
            401: OpenApiResponse(description='Требуется авторизация'),
            403: OpenApiResponse(description='Удалять можно только свой профиль'),
        },
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """CRUD пользователей. create — регистрация (без токена)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsUserProfileOwner()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        # без get_object()! (см. пункт 1)
        if self.action == 'list':
            return UserPublicSerializer
        return UserSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer_class = (
            UserProfileSerializer if instance == request.user else UserPublicSerializer
        )
        serializer = serializer_class(instance, context=self.get_serializer_context())
        return Response(serializer.data)


class PaymentCreateAPIView(APIView):
    """Создание платежа: продукт + цена + сессия в Stripe, в ответе — ссылка на оплату."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PaymentCreateRequestSerializer,
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(description='Некорректный course_id или у курса не задана цена'),
            401: OpenApiResponse(description='Требуется авторизация'),
            404: OpenApiResponse(description='Курс не найден'),
            502: OpenApiResponse(description='Ошибка платёжного сервиса Stripe'),
        },
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
            product_id=product.id,
            price_id=price.id,
            session_id=session.id,
            payment_link=session.url,
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentStatusAPIView(APIView):
    """Статус платежа в Stripe по id сессии; статус сохраняется в модель Payment."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: PaymentStatusSerializer,
            401: OpenApiResponse(description='Требуется авторизация'),
            404: OpenApiResponse(description='Платёж с такой сессией не найден'),
            502: OpenApiResponse(description='Ошибка платёжного сервиса Stripe'),
        },
        tags=['payments'],
    )
    def get(self, request, session_id, *args, **kwargs):
        payment = get_object_or_404(Payment, session_id=session_id, user=request.user)
        try:
            session = services.retrieve_session(session_id)
        except stripe.StripeError as exc:
            return Response(
                {'error': f'Ошибка платёжного сервиса Stripe: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if payment.payment_status != session.payment_status:
            payment.payment_status = session.payment_status
            payment.save(update_fields=['payment_status'])

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
