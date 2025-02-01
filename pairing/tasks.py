from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import OuterRef, Subquery

from debate.models import Stance
from notifications.models import Notification
from .models import PairingRequest, PairingMatch
from datetime import timedelta, datetime

from collections import deque

logger = get_task_logger(__name__)
GRACE_PERIOD = timedelta(minutes=5)


@transaction.atomic
def create_match(pairing_request, other_pairing_request):
    """
    Creates a PairingMatch between the two pairing requests.
    It also creates the related discussion and the notifications for the participants.

    returns the PairingMatch object.
    """
    pairing_match = PairingMatch.objects.create(
        pairing_request_1=pairing_request,
        pairing_request_2=other_pairing_request
    )

    # Complete the match
    related_discussion = pairing_match.complete_match()

    # If any of the participants is online, we will add the discussion to their list of discussions live
    related_discussion.add_discussion_to_participants_list_live()

    # Send the notification to the participants
    Notification.objects.create_new_discussion_notification(
        pairing_request.user_id,
        other_pairing_request.user.username,
        related_discussion.id,
        related_discussion.debate.title
    )
    Notification.objects.create_new_discussion_notification(
        other_pairing_request.user_id,
        pairing_request.user.username,
        related_discussion.id,
        related_discussion.debate.title
    )

    return pairing_match


@transaction.atomic
def try_pairing_passive_requests_in_debate(locked_requests):
    """
    Tries to pair passive pairing requests for a given debate.
    This function assumes that the requests are already sorted by the time they were created.
    You should also lock the requests before calling this function to prevent race conditions.
    """
    unmatched_requests = {
        'wants_for': {
            'is_for': deque(),
            'is_against': deque()
        },
        'wants_against': {
            'is_for': deque(),
            'is_against': deque()
        }
    }

    pairing_matches = []
    for request in locked_requests:
        # Determine where the matching queue is.
        # The user of the current request wants to debate someone who is_for or is_against
        # A matching request would wants_for or wants_against
        matching_queue_stance = 'is_for' if request.desired_stance else 'is_against'
        matching_queue_desire = 'wants_for' if request.user_stance else 'wants_against'

        # Get the queue of unmatched requests that would match with this request
        matching_queue = unmatched_requests[matching_queue_desire][matching_queue_stance]

        if not matching_queue:
            # If there are no requests in the queue, we need to add this request in its own queue
            request_stance = 'is_for' if request.user_stance else 'is_against'
            request_desire = 'wants_for' if request.desired_stance else 'wants_against'
            request_queue = unmatched_requests[request_desire][request_stance]
            request_queue.append(request)
        else:
            # If there are requests in the queue, we can match with the oldest one (first in the queue)
            oldest_matching_request = matching_queue.popleft()
            try:
                pairing_match = create_match(request, oldest_matching_request)
            except Exception as e:  # noqa
                # If the match fails, we need to put the oldest_matching_request back in the queue
                # TODO: log the error
                logger.error(f'Error creating match: {e}')
                matching_queue.appendleft(oldest_matching_request)
            else:
                pairing_matches.append(pairing_match)

    return pairing_matches


@shared_task
def try_pairing_passive_requests():
    """
    Attempts to pair passive pairing requests for all debates.

    To give enough time for each request to be matched with high quality matches, it only considers
    pairing requests that have been created at least 5 minutes ago.

    TODO: ensure the whole thing doesnt fail if a single pairing match fails
    """
    logger.info('Trying to pair passive requests')

    # Get all debates with passive pairing requests that are at least 5 minutes old
    debates = PairingRequest.objects.filter(
        status=PairingRequest.Status.PASSIVE,
        created_at__lte=datetime.now() - GRACE_PERIOD
    ).values_list('debate', 'debate__title').distinct()

    # Define the user_stance subquery
    user_stance = Subquery(
        Stance.objects.filter(
            debate=OuterRef('debate'),
            user=OuterRef('user')
        ).values('stance')[:1]
    )

    logger.info(f'Found {len(debates)} debates with passive requests')

    for debate_id, debate_title in debates:
        logger.info(f'Pairing requests for debate {debate_id} ({debate_title})')

        # Get all passive pairing requests for this debate
        requests = PairingRequest.objects.select_for_update(
            of=('self',)
        ).filter(
            debate=debate_id,
            status=PairingRequest.Status.PASSIVE,
            created_at__lte=datetime.now() - GRACE_PERIOD
        ).annotate(
            user_stance=user_stance
        ).order_by('created_at')

        try:
            pairing_matches = try_pairing_passive_requests_in_debate(requests)
        except Exception as e:  # noqa
            # If the pairing fails, we need to log the error
            logger.error(f'Error pairing requests (debate {debate_id}): {e}')
            continue

        logger.info(
            f'Paired {2 * len(pairing_matches)} requests in debate {debate_id}. There are now {len(requests) - 2 * len(pairing_matches)} requests left.')
