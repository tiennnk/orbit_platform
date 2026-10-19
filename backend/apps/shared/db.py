from django.db import IntegrityError


def violated_constraint(exc: IntegrityError) -> str | None:
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)
