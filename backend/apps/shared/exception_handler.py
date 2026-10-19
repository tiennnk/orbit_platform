from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.shared.exceptions import ConflictError, NotFoundError, UnavailableError

STATUS_BY_ERROR = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    UnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def custom_exception_handler(exc, context):
    for error_class, status_code in STATUS_BY_ERROR.items():
        if isinstance(exc, error_class):
            return Response({"detail": str(exc)}, status=status_code)

    return exception_handler(exc, context)
