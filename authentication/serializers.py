# authentication/serializers.py
from rest_framework import serializers

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    name = serializers.CharField(required=True)
    department = serializers.CharField(required=False, allow_blank=True)
    institution = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, default='teacher')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs


class UserSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.CharField()
    department = serializers.CharField(required=False, allow_blank=True)
    institution = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(read_only=True)
    date_joined = serializers.CharField(read_only=True)  # Changed from DateTimeField to CharField

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)