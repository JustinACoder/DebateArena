from pairing.models import PairingRequest


class PairingMiddleware:
    """Adds current_pairing_request to request if user is authenticated and has an active or idle pairing request."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.current_pairing_request = PairingRequest.objects.get_current_request(request.user)

        response = self.get_response(request)

        return response
