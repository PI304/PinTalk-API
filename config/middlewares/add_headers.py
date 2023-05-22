class AddHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Link"] = 'https://api.pintalk.app/api/swagger; rel="profile"'
        return response
