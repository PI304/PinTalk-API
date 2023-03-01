from rest_framework.permissions import BasePermission, SAFE_METHODS


class AuthenticatedClientOnly(BasePermission):
    message = "request domain not allowed"

    def has_object_permission(self, request, view, obj) -> bool:
        host = request.headers.get("Host", None)
        print(host)
        if host != obj.service_domain:
            return False

        return True
