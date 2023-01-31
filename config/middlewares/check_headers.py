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
                request.headers["X-PinTalk-Access-Key"]
                and request.headers["X-PinTalk-Secret-Key"]
            ):
                raise ValidationError(
                    "'X-PinTalk-Access-Key' and 'X-PinTalk-Secret-Key' header must be present"
                )
