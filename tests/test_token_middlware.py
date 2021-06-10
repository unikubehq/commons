from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from commons.middleware.token_middleware import TokenMiddleware


def get_response(cls, request):
    return HttpResponse()


class TokenMiddlewareTest(TestCase):

    middleware = TokenMiddleware(get_response=get_response)

    def setUp(self) -> None:
        super(TokenMiddlewareTest, self).setUp()
