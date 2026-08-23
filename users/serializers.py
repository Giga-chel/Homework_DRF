from rest_framework import serializers
from .models import User, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        exclude = ['password', 'last_login', 'is_superuser', 'is_staff', 'is_active', 'groups', 'user_permissions']
