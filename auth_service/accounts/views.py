from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
import requests

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .serializers import (
    RegisterSerializer,
    ProfileSerializer,
    AvatarUploadSerializer,
    VerifyOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
)
from .utils import (
    generate_otp,
    save_otp_to_redis,
    get_otp_from_redis,
    delete_otp,
)
from .tasks import send_email_async

User = get_user_model()

# -------------------------------------------------------------------
# REGISTER + EMAIL OTP
# -------------------------------------------------------------------

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = generate_otp()
        save_otp_to_redis(user.email, otp)

        send_email_async.delay(
            "Verify Your Synq Account",
            f"Your verification OTP is: {otp}",
            user.email,
        )

        return Response(
            {"detail": "User registered. OTP sent to email."},
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "User not found"}, status=404)

        saved = get_otp_from_redis(email)
        if not saved:
            return Response({"detail": "OTP expired"}, status=400)

        if saved != otp:
            return Response({"detail": "Invalid OTP"}, status=400)

        user.email_verified = True
        user.save()
        delete_otp(email)

        return Response({"detail": "Email verified successfully"})


# -------------------------------------------------------------------
# LOGIN (EMAIL + PASSWORD)
# -------------------------------------------------------------------

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=email, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=401)

        if not user.email_verified:
            return Response({"detail": "Email not verified"}, status=403)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


# -------------------------------------------------------------------
# GOOGLE LOGIN
# -------------------------------------------------------------------

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response(
                {"detail": "id_token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception:
            return Response(
                {"detail": "Invalid Google token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = idinfo.get("email")
        name = idinfo.get("name", "")

        if not email:
            return Response(
                {"detail": "Google account has no email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "full_name": name,
                "email_verified": True,
            },
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


# -------------------------------------------------------------------
# PROFILE + AVATAR
# -------------------------------------------------------------------

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = AvatarUploadSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Avatar updated"})


# -------------------------------------------------------------------
# PASSWORD RESET (OTP)
# -------------------------------------------------------------------

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user:
            otp = generate_otp()
            save_otp_to_redis(email, otp)

            send_email_async.delay(
                "Reset Password OTP",
                f"Your password reset OTP is: {otp}",
                email,
            )

        return Response(
            {"detail": "If email exists, OTP sent"},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_pw = serializer.validated_data["new_password"]

        saved = get_otp_from_redis(email)
        if not saved or saved != otp:
            return Response({"detail": "Invalid or expired OTP"}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "User not found"}, status=404)

        user.set_password(new_pw)
        user.save()
        delete_otp(email)

        return Response({"detail": "Password reset successful"})


# -------------------------------------------------------------------
# CHANGE PASSWORD (LOGGED IN)
# -------------------------------------------------------------------

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_pw = serializer.validated_data["old_password"]
        new_pw = serializer.validated_data["new_password"]

        user = request.user
        if not user.check_password(old_pw):
            return Response(
                {"detail": "Old password incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_pw)
        user.save()

        return Response({"detail": "Password changed successfully"})
