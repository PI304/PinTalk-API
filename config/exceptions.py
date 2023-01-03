from django.core.exceptions import BadRequest
from rest_framework.views import exception_handler
from rest_framework import exceptions
from django.http import Http404
from rest_framework.exceptions import APIException


class InstanceNotFound(APIException):
    status_code = 404
    default_detail = "Not Found"
    default_code = "not_found"

    def __init__(self, detail=None):
        if detail is None:
            self.detail = self.default_detail
        else:
            self.detail = detail


class DuplicateInstance(APIException):
    status_code = 409
    default_detail = "Instance with provided data already exists"
    default_code = "duplicate_instance"

    def __init__(self, detail=None):
        if detail is None:
            self.detail = self.default_detail
        else:
            self.detail = detail


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Update the structure of the response data.
    if response is not None:
        if isinstance(exc, Http404):
            customized_response = {"code": response.status_code, "detail": "Not Found"}
        elif isinstance(exc, exceptions.NotFound):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.MethodNotAllowed):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.NotAcceptable):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.UnsupportedMediaType):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.AuthenticationFailed):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.PermissionDenied):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, exceptions.NotAuthenticated):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, InstanceNotFound):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        elif isinstance(exc, DuplicateInstance):
            customized_response = {"code": response.status_code, "detail": exc.detail}
        else:
            customized_response = {
                "code": response.status_code,
                "detail": response.data,
            }

        response.data = customized_response

    return response
