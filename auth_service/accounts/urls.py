from django.urls import path
from .views import (
    RegisterView,
    VerifyOTPView,
    LoginView,
    ProfileView,
    AvatarUploadView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    GoogleLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("login/", LoginView.as_view(), name="login"),

    path("profile/", ProfileView.as_view(), name="profile"),
    path("avatar/", AvatarUploadView.as_view(), name="avatar-upload"),

    path("forgot/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path("google-login/", GoogleLoginView.as_view(), name="google-login"),
]
