from datetime import datetime

from django.db.models import Q, Count, Subquery, Sum, OuterRef
from django.db.models.functions import Coalesce

from discussion.models import ReadCheckpoint, Discussion


class MessageMiddleware:
    """Adds num_unread_messages to the request, user object."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Subquery to get the latest read message timestamp for each discussion
            last_read_timestamp = ReadCheckpoint.objects.filter(
                user=request.user,
                discussion=OuterRef('pk')
            ).values('last_message_read__created_at')[:1]

            # Query to get the count of messages that are after the checkpoint for each discussion
            unread_messages_query = (
                Discussion.objects
                .filter((Q(participant1=request.user) & Q(is_archived_for_p1=False)) |
                        (Q(participant2=request.user) & Q(is_archived_for_p2=False)))
                .annotate(
                    unread_count=Count(
                        'message',
                        filter=Q(message__created_at__gt=Coalesce(Subquery(last_read_timestamp), datetime.min))
                    )
                )
            )

            # Get the total number of unread messages
            request.user.num_unread_messages = unread_messages_query.aggregate(Sum('unread_count'))['unread_count__sum']

        response = self.get_response(request)

        return response
