from django.conf import settings
from jwt import JWT

from commons.keycloak.client import get_authz_client
from commons.keycloak.permissions import KeycloakPermissions


class KCPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allow_kc_access_tokens = getattr(settings, "ALLOW_ACCESS_TOKENS", True)
        self.authz_client = get_authz_client()

    def __call__(self, request):

        if "x-forwarded-access-token" in request.headers:
            token_raw = request.headers["x-forwarded-access-token"]
            token = JWT().decode(token_raw, do_verify=False)
        else:
            token_raw = None
            token = None

        if token:
            # set the user's profile for this request
            request.kcuser = {
                "uuid": token["sub"],
                "email": token["email"],
                "name": token.get("name"),
                "family_name": token.get("family_name"),
                "given_name": token.get("given_name"),
            }
            # put the token for future use
            # code should not relay on it
            request._token = token

            if "authorization" in token:
                # this is a proper RPT with permissions in request
                request.permissions = KeycloakPermissions(token["authorization"]["permissions"])
            else:
                if token_raw and self.allow_kc_access_tokens:
                    permission_list = self.authz_client.get_permissions(token_raw)
                    request.permissions = KeycloakPermissions(permission_list["permissions"])
                else:
                    # apollo schema-polling queries are currently not with authorization
                    pass
                    # return HttpResponse("Permissions are not in RPT and ALLOW_ACCESS_TOKENS is set to False", status=401)

        response = self.get_response(request)
        return response
