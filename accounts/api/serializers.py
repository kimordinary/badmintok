from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from accounts.models import User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer"""
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'activity_name', 'auth_provider', 'profile_image_url', 'date_joined']
        read_only_fields = ['id', 'email', 'auth_provider', 'date_joined']
    
    def get_profile_image_url(self, obj):
        """프로필 이미지 URL 반환"""
        return obj.profile_image_url


class UserSignupSerializer(serializers.Serializer):
    """회원가입 Serializer"""
    email = serializers.EmailField(required=True)
    activity_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label='비밀번호 확인')
    terms_agreed = serializers.BooleanField(required=True)
    privacy_agreed = serializers.BooleanField(required=True)
    
    def validate_email(self, value):
        """이메일 중복 검사"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value
    
    def validate(self, attrs):
        """비밀번호 일치 확인"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "비밀번호와 비밀번호 확인이 일치하지 않습니다."})
        return attrs
    
    def validate_terms_agreed(self, value):
        """이용약관 동의 확인"""
        if not value:
            raise serializers.ValidationError("이용약관에 동의해주세요.")
        return value
    
    def validate_privacy_agreed(self, value):
        """개인정보처리방침 동의 확인"""
        if not value:
            raise serializers.ValidationError("개인정보처리방침에 동의해주세요.")
        return value
    
    def create(self, validated_data):
        """사용자 생성"""
        user = User.objects.create_user(
            email=validated_data['email'],
            activity_name=validated_data['activity_name'],
            password=validated_data['password']
        )
        # UserProfile 자동 생성
        UserProfile.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """로그인 Serializer (직렬화용, 실제 인증은 view에서 처리)"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class KakaoLoginSerializer(serializers.Serializer):
    """카카오 로그인 Serializer"""
    access_token = serializers.CharField(required=True, write_only=True)

