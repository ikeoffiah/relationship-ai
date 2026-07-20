from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.serializers import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    DRF's default handler only understands APIException subclasses, so a
    django.core.exceptions.ValidationError raised from a model's clean()/save()
    escapes as a 500. Translate it into DRF's ValidationError so model-level
    validation surfaces as a 400 like serializer-level validation does.
    """
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail=exc.messages)

    return drf_exception_handler(exc, context)
