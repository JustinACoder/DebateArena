

class NotificationMiddleware:
    """Adds num_unread_notifications to the request,user object."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.num_unread_notifications = request.user.notification_set.filter(read=False).count()

        response = self.get_response(request)

        return response
