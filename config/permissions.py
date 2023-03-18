from rest_framework.permissions import BasePermission, SAFE_METHODS


class AuthenticatedClientOnly(BasePermission):
    message = "request domain not allowed"

    def has_object_permission(self, request, view, obj) -> bool:
        host = request.headers.get("Host", None)
        print(host)
        if host != obj.service_domain:
            return False

        return True


class HostOnly(BasePermission):
    message = "only the host can modify chatroom resources"

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.host_id != request.user.id:
            return False


class RequestUserOnly(BasePermission):
    message = "only request user can modify user configuration"

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.user_id != request.user.id:
            return False


class ClientWithHeadersOnly(BasePermission):
    message = "custom headers not present"

    def has_permission(self, request, view) -> bool:
        print(request.headers)
        if (
            not request.headers["X-Pintalk-Access-Key"]
            or not request.headers["X-Pintalk-Secret-Key"]
        ):
            print("permission denied")
            return False
        else:
            return True
