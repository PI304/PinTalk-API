from rest_framework.exceptions import ValidationError


class CheckHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        self.process_request(request)
        response = self.get_response(request)

        return response

    def process_request(self, request):
        if "client" in request.path:
            if not (
                request.headers["X-ChatBox-Access-Key"]
                and request.headers["X-ChatBox-Secret-Key"]
            ):
                raise ValidationError(
                    "'X-ChatBox-Access-Key' and 'X-ChatBox-Secret-Key' header must be present"
                )
