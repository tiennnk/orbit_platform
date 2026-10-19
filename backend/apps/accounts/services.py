from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token

from apps.shared.exceptions import ConflictError


class UsernameTaken(ConflictError):
    pass


class InvalidCredentials(Exception):
    pass


def register_user(*, username: str, password: str) -> tuple[AbstractBaseUser, str]:
    try:
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=username, password=password
            )
            token = Token.objects.create(user=user)
    except IntegrityError as exc:
        raise UsernameTaken("This username is taken.") from exc
    return user, token.key


def login(*, username: str, password: str) -> tuple[AbstractBaseUser, str]:
    user = authenticate(username=username, password=password)
    if user is None:
        raise InvalidCredentials
    token, _ = Token.objects.get_or_create(user=user)
    return user, token.key


def logout(*, user: AbstractBaseUser) -> None:
    Token.objects.filter(user=user).delete()


def change_password(*, user: AbstractBaseUser, new_password: str) -> str:
    with transaction.atomic():
        user.set_password(new_password)
        user.save(update_fields=["password"])
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
    return token.key
