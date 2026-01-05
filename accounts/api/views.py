from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
import requests
from urllib.parse import urlparse
import os
import datetime
from django.core.files.base import ContentFile
from django.conf import settings

from accounts.models import User, UserProfile
from accounts.api.serializers import (
    UserSerializer, UserSignupSerializer, KakaoLoginSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """회원가입 API"""
    serializer = UserSignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user_serializer = UserSerializer(user)
        
        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': '회원가입이 완료되었습니다.',
            'user': user_serializer.data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """로그인 API"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': '이메일과 비밀번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
        if not user.check_password(password):
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not user.is_active:
            return Response(
                {'error': '비활성화된 계정입니다. 관리자에게 문의하세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except User.DoesNotExist:
        return Response(
            {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # JWT 토큰 생성
    refresh = RefreshToken.for_user(user)
    user_serializer = UserSerializer(user)
    
    return Response({
        'message': '로그인되었습니다.',
        'user': user_serializer.data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """로그아웃 API"""
    # JWT는 stateless이므로 클라이언트에서 토큰을 삭제하도록 안내
    # 필요시 Refresh Token을 무효화할 수 있지만, blacklist 기능이 필요
    return Response({'message': '로그아웃되었습니다. 토큰을 삭제해주세요.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """토큰 갱신 API"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            return Response({
                'access': str(token.access_token),
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'refresh 토큰이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': '유효하지 않은 토큰입니다.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """현재 사용자 정보 조회 API"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def kakao_login(request):
    """카카오 소셜 로그인 API"""
    serializer = KakaoLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    access_token = serializer.validated_data['access_token']
    
    try:
        # 카카오 사용자 정보 가져오기
        user_info_response = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
    except requests.RequestException:
        return Response(
            {'error': '카카오 사용자 정보를 가져오는 데 실패했습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    kakao_account = user_info.get("kakao_account", {})
    email = kakao_account.get("email")
    profile = kakao_account.get("profile", {})
    nickname = profile.get("nickname")
    profile_image_url = profile.get("profile_image_url")
    is_default_image = profile.get("is_default_image", True)
    gender = kakao_account.get("gender")
    age_range = kakao_account.get("age_range")
    birthday = kakao_account.get("birthday")  # MMDD 형식
    birthyear = kakao_account.get("birthyear")
    phone_number = kakao_account.get("phone_number")
    
    if not email:
        return Response(
            {'error': '카카오 계정에서 이메일 정보를 제공하지 않았습니다. 카카오 설정을 확인해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 사용자 생성 또는 가져오기
    defaults = {
        "activity_name": nickname or email.split("@")[0],
        "auth_provider": "kakao"
    }
    user, created = User.objects.get_or_create(email=email, defaults=defaults)
    
    if created:
        user.set_unusable_password()
        user.save()
    else:
        # 기존 사용자도 카카오 로그인으로 업데이트
        update_fields = []
        if not user.auth_provider:
            user.auth_provider = "kakao"
            update_fields.append("auth_provider")
        if nickname and user.activity_name != nickname:
            user.activity_name = nickname
            update_fields.append("activity_name")
        if update_fields:
            user.save(update_fields=update_fields)
    
    # 프로필 업데이트
    profile_defaults = {}
    if nickname:
        profile_defaults["name"] = nickname
    
    if gender:
        gender_map = {
            "male": UserProfile.Gender.MALE,
            "female": UserProfile.Gender.FEMALE,
        }
        profile_defaults["gender"] = gender_map.get(gender, UserProfile.Gender.OTHER)
    
    if age_range:
        profile_defaults["age_range"] = age_range
    if birthyear and birthyear.isdigit():
        profile_defaults["birth_year"] = int(birthyear)
    if birthday and len(birthday) == 4:
        try:
            birth_month = int(birthday[:2])
            birth_day = int(birthday[2:])
            birth_year_value = int(birthyear) if birthyear and birthyear.isdigit() else 1900
            profile_defaults["birthday"] = datetime.date(birth_year_value, birth_month, birth_day)
        except ValueError:
            pass
    if phone_number:
        profile_defaults["phone_number"] = phone_number
    
    profile_obj, created_profile = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults)
    
    update_fields = set()
    if not created_profile:
        for field, value in profile_defaults.items():
            if value and getattr(profile_obj, field) != value:
                setattr(profile_obj, field, value)
                update_fields.add(field)
    
    default_profile_path = "images/userprofile/user.png"
    
    if is_default_image:
        current_name = profile_obj.profile_image.name if profile_obj.profile_image else ""
        if current_name and current_name != default_profile_path:
            try:
                profile_obj.profile_image.delete(save=False)
            except Exception:
                pass
        if current_name != default_profile_path:
            profile_obj.profile_image.name = default_profile_path
            update_fields.add("profile_image")
    elif profile_image_url:
        try:
            image_response = requests.get(profile_image_url, timeout=5)
            image_response.raise_for_status()
            parsed = urlparse(profile_image_url)
            basename = os.path.basename(parsed.path.rstrip("/"))
            base, _ = os.path.splitext(basename)
            file_name = f"kakao_{user.id}.jpg"
            storage = profile_obj.profile_image.field.storage
            save_path = f"images/userprofile/{file_name}"
            stored_path = storage.save(save_path, ContentFile(image_response.content))
            if profile_obj.profile_image.name != stored_path:
                profile_obj.profile_image.name = stored_path
                update_fields.add("profile_image")
        except requests.RequestException:
            pass
    
    if update_fields:
        profile_obj.save(update_fields=list(update_fields))
    
    # JWT 토큰 생성
    refresh = RefreshToken.for_user(user)
    user_serializer = UserSerializer(user)
    
    return Response({
        'message': '카카오 계정으로 로그인되었습니다.',
        'user': user_serializer.data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    }, status=status.HTTP_200_OK)

