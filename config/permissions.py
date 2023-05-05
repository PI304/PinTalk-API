from rest_framework.permissions import BasePermission, SAFE_METHODS


class AuthorizedOriginOnly(BasePermission):
    message = "request domain not allowed"

    def has_object_permission(self, request, view, obj) -> bool:
        origin = request.headers.get("Origin")
        if obj.service_domain == origin.split("//")[1]:
            return True
        return False


class HostOnly(BasePermission):
    message = "only the host can access chatroom resources"

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.host_id != request.user.id:
            return False
        return True


class RequestUserOnly(BasePermission):
    message = "only request user can modify user configuration"

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.user_id != request.user.id:
            return False


class ClientWithHeadersOnly(BasePermission):
    message = "custom headers not present"

    def has_permission(self, request, view) -> bool:
        if (
            not request.headers["X-Pintalk-Access-Key"]
            or not request.headers["X-Pintalk-Secret-Key"]
        ):
            return False
        else:
            return True


class ActivatedUserOnly(BasePermission):
    message = "this user is deactivated"

    def has_permission(self, request, view) -> bool:
        if request.user.is_deleted:
            return False
        return True
