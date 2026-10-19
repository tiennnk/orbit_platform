from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.accounts.services import (
    InvalidCredentials,
    change_password,
    login,
    logout,
    register_user,
)
from apps.shared.serializers import ErrorSerializer


def _auth_response(user, token: str) -> dict:
    return {"token": token, "user": UserSerializer(user).data}


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        operation_id="register",
        auth=[],
        request=RegisterSerializer,
        responses={201: AuthResponseSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, token = register_user(**serializer.validated_data)
        return Response(_auth_response(user, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        operation_id="login",
        auth=[],
        request=LoginSerializer,
        responses={200: AuthResponseSerializer, 401: ErrorSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, token = login(**serializer.validated_data)
        except InvalidCredentials:
            return Response(
                {"detail": "Wrong username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(_auth_response(user, token))


class MeView(APIView):
    @extend_schema(tags=["auth"], operation_id="getMe", responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    @extend_schema(
        tags=["auth"], operation_id="logout", request=None, responses={204: None}
    )
    def post(self, request):
        logout(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(APIView):
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        operation_id="changePassword",
        request=PasswordChangeSerializer,
        responses={200: AuthResponseSerializer},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)

        token = change_password(
            user=request.user, new_password=serializer.validated_data["new_password"]
        )
        return Response(_auth_response(request.user, token))
