from django.conf import settings
from jwt import JWT


class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        authorization_header = request.headers.get("Authorization")
        if not authorization_header or not authorization_header.startswith("Bearer"):
            return self.get_response(request)

        verifying_key = settings.JWT_VERIFYING_KEY

        instance = JWT()
        encoded_token = authorization_header.split(" ")[-1]
        token = instance.decode(encoded_token, verifying_key, do_time_check=True, do_verify=True)

        request.token = token

        return self.get_response(request)
