from django.contrib.auth.models import update_last_login
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError

from config.exceptions import DuplicateInstance
from .models import User
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.hashers import check_password
from django.core.mail import EmailMessage

from .serializers import UserSerializer
from .services import UserService


class BasicSignUpView(APIView):
    serializer_class = UserSerializer

    @swagger_auto_schema(
        operation_summary="Sign up",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "email",
                "service_name",
                "service_expl",
                "password",
                "confirm_password",
            ],
            properties={
                "email": openapi.Schema(
                    type=openapi.FORMAT_EMAIL, description="가입하려는 이메일"
                ),
                "service_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="운영하려는 서비스의 이름"
                ),
                "service_expl": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="서비스 설명",
                ),
                "password": openapi.Schema(type=openapi.FORMAT_PASSWORD),
                "confirm_password": openapi.Schema(type=openapi.FORMAT_PASSWORD),
            },
        ),
        responses={
            201: openapi.Response("user", UserSerializer),
            400: "Passwords doesn't match",
        },
    )
    def post(self, request, *args, **kwargs):

        password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("Passwords doesn't match")

        email = request.data.get("email")
        service_name = request.data.get("service_name")
        service_expl = request.data.get("service_expl")

        access_key = UserService.generate_access_key()
        secret_key = UserService.generate_secret_key()

        user = User.objects.create_user(
            email=email,
            password=password,
            service_name=service_name,
            service_expl=service_expl,
            access_key=access_key,
            secret_key=secret_key,
        )

        serializer = UserSerializer(user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BasicSignInView(APIView):
    serializer = UserSerializer

    @swagger_auto_schema(
        operation_summary="Sign In",
        responses={
            201: openapi.Response("user", UserSerializer),
            401: "Incorrect password",
        },
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        try:
            user = get_object_or_404(User, email=email)
        except Http404:
            raise AuthenticationFailed("No user by the provided email")

        if not check_password(password, user.password):
            raise AuthenticationFailed("Incorrect password")

        update_last_login(None, user)
        serializer = UserSerializer(user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SecessionView(APIView):
    serializer = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Leave",
        responses={200: openapi.Response("user", UserSerializer)},
    )
    def post(self, request, *args, **kwargs):
        service = UserService(request.user, request)
        user = service.deactivate_user()
        serializer = UserSerializer(user)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CheckDuplicateUsernameView(APIView):
    @swagger_auto_schema(
        operation_summary="Check if there's duplicate email (username)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"email": openapi.Schema(type=openapi.FORMAT_EMAIL)},
        ),
        responses={
            200: openapi.Response(
                description="No duplicates",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "email": openapi.Schema(
                            type=openapi.TYPE_STRING, description="email"
                        ),
                    },
                ),
            ),
            409: "Provided email already exists",
        },
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")

        existing_email = User.objects.filter(email=email).first()
        if existing_email:
            raise DuplicateInstance("Provided email already exists")

        return Response({"email": email}, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    serializer = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change user password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "currentPassword": openapi.Schema(type=openapi.FORMAT_PASSWORD),
                "newPassword": openapi.Schema(type=openapi.FORMAT_PASSWORD),
            },
        ),
        responses={
            200: openapi.Response("Success", UserSerializer),
            401: "Password do not match",
        },
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not check_password(current_password, user.password):
            raise AuthenticationFailed("Password do not match")

        user.set_password(new_password)
        user.updated_at = timezone.now()
        user.save(update_fields=["password", "updated_at"])

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset password to random string sent to user email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"email": openapi.Schema(type=openapi.FORMAT_EMAIL)},
        ),
        responses={
            404: "User with the provided email does not exist",
            500: "Failed to send email. Try again later.",
        },
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")

        try:
            user = get_object_or_404(User, email=email)
        except Http404:
            raise NotFound("User with the provided email does not exist")

        new_password = UserService.generate_random_code(3, 8)
        user.set_password(new_password)
        user.save(update_fields=["password"])

        email = EmailMessage(
            "[PinTalk] 비밀번호가 초기화 되었습니다.",
            f"비밀번호가 아래의 임시 비밀번호로 변경되었습니다. 아래 비밀번호로 다시 로그인하신 뒤 꼭 비밀번호를 변경해주세요.\n임시 비밀번호: {new_password}",
            to=[email],  # 받는 이메일
        )
        success = email.send()

        if success > 0:
            return Response(status=status.HTTP_200_OK)
        elif success == 0:
            return Response(
                {"details": "Failed to send email. Try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailVerification(APIView):
    @swagger_auto_schema(
        operation_summary="Send verification code to user email when signing up",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"email": openapi.Schema(type=openapi.FORMAT_EMAIL)},
        ),
        responses={
            500: "Failed to send email. Try again later or try with a valid email."
        },
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        generated_code = UserService.generate_random_code(5, 8)

        # set code in cookie
        res = JsonResponse({"success": True})
        # TODO: httponly, secure options
        res.set_cookie("email_verification_code", generated_code, max_age=300)

        # send email
        email = EmailMessage(
            "[PinTalk] 이메일 인증 코드입니다.",
            generated_code,
            to=[email],  # 받는 이메일
        )
        success = email.send()

        if success > 0:
            return Response(status=status.HTTP_200_OK)
        elif success == 0:
            return Response(
                {
                    "details": "Failed to send email. Try again later or try with a valid email."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailConfirmation(APIView):
    @swagger_auto_schema(
        operation_summary="Confirm code sent to email for signing up",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"verification_code": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={
            400: "No cookies attached",
            409: "Verification code does not match",
        },
    )
    def post(self, request, *args, **kwargs):
        if "email_verification_code" in request.COOKIES:
            code_cookie = request.COOKIES.get("email_verification_code")
        else:
            return Response(
                {"detail": "No cookies attached"}, status=status.HTTP_400_BAD_REQUEST
            )

        code_input = request.data.get("verification_code")
        if code_cookie == code_input:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": "Verification code does not match"},
                status=status.HTTP_409_CONFLICT,
            )
