import time

from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Window, F, BooleanField, When, Case, Value, TextField, OuterRef, Subquery, Max
from django.contrib.auth.decorators import login_required
from django.db.models.functions import FirstValue, Coalesce, Greatest
from django.shortcuts import render, get_object_or_404, redirect
from django.db import connection
from django.views.decorators.http import require_POST, require_GET

from debate.models import Debate
from discussion.forms import MessageForm
from discussion.models import Discussion, Message
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseNotFound


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.

    Source: https://docs.djangoproject.com/en/5.0/topics/db/sql/
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_most_recent_discussions_queryset(user):
    """
    Get a queryset with the most recent discussions for the user. A discussion datetime is the maximum datetime
    between the discussion creation datetime and the most recent message datetime if the discussion has messages.

    :param user: User instance
    :return: Queryset of discussions with the most recent datetime
    """
    # TODO: denormalize the db by adding a latest_message one-to-one field to Discussion for large scale
    return Discussion.objects.annotate(
        latest_message_date=Max('message__created_at'),  # Using reverse relation from Discussion to Message
        latest_message_text=Max('message__text'),
        latest_message_author=Max('message__author__username'),
    ).annotate(
        recent_date=Greatest(
            'created_at',
            F('latest_message_date')  # Handling null cases directly with Greatest
        )
    ).filter(
        Q(participant1=user) | Q(participant2=user)
    ).select_related('debate').order_by('-recent_date')


@login_required
def discussion_default(request):
    # Get the most recent discussion
    most_recent_discussion = get_most_recent_discussions_queryset(request.user).first()
    most_recent_discussion_id = most_recent_discussion.id if most_recent_discussion else None
    return specific_discussion(request, most_recent_discussion_id)


@login_required
def specific_discussion(request, discussion_id):
    # If the current user is not a participant in the discussion, return 403
    if discussion_id is not None and not Discussion.objects.filter(Q(participant1=request.user) | Q(participant2=request.user), pk=discussion_id).exists():
        return HttpResponseForbidden()

    context = {
        'message_form': MessageForm(),
        'discussion_id': discussion_id
    }

    return render(request, 'discussion/discussion_board.html', context=context)


@login_required
def get_discussion_page(request):
    discussions_queryset = get_most_recent_discussions_queryset(request.user)

    # Get the page
    paginator = Paginator(discussions_queryset, 15)
    page = paginator.get_page(request.GET.get('page', '1'))

    return render(request, 'discussion/discussion_list_page.html', {'page': page})



@login_required
@require_GET
def retrieve_messages(request, discussion_id):
    # Note: I decided not to use Paginator or django-el-pagination for this since it is pretty simple and would be
    # more complex to implement with those tools.

    # Get page number and determine if the user wants discussion info
    page = request.GET.get('page', '1')  # Starts at 1
    include_discussion_info = request.GET.get('include_discussion_info', 'false')

    # Ensure that the values are valid
    if not page.isdigit() or not include_discussion_info in ['true', 'false']:
        return HttpResponseBadRequest()

    page = int(page)
    include_discussion_info = include_discussion_info == 'true'

    # From the page number, calculate the start (inclusive) and end (exclusive) indexes
    first_page_size = settings.ENDLESS_PAGINATION_SETTINGS['FIRST_PAGE_SIZE']
    other_page_size = settings.ENDLESS_PAGINATION_SETTINGS['PAGE_SIZE']
    if page == 1:
        start = 0
        end = first_page_size
    else:
        start = first_page_size + (page - 2) * other_page_size
        end = start + other_page_size

    # Get messages and discussion info
    discussion_instance = get_object_or_404(
        Discussion.objects  # TODO: should we return 403 if the user is not a participant?
        .filter(Q(participant1=request.user) | Q(participant2=request.user))
        .prefetch_related('message_set')
        .select_related('debate', 'participant1', 'participant2'), pk=discussion_id)
    messages = (discussion_instance.message_set.order_by('-created_at').annotate(
        is_current_user=Case(
            When(author=request.user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).values('id', 'author__username', 'text', 'created_at', 'is_current_user'))

    # Initialize response data
    # To determine if there is a next page, we try to get one more message than the page size
    # If we retrieve page size + 1 messages, there is a next page, otherwise there isn't
    # If there is a next page, we remove the last message from the results since it belongs to the next page
    # Otherwise, we return all the messages since they all belong to the current page
    results = list(messages[start:end + 1])
    expected_message_count = end - start + 1
    has_next = len(results) == expected_message_count
    messages_to_return = results[:-1] if has_next else results
    data = {'messages': messages_to_return, 'has_next': has_next}

    # If the user wants discussion info, include it in the response
    if include_discussion_info:
        data['discussion'] = {
            'id': discussion_instance.id,
            'debate': discussion_instance.debate.title,
            'participants': [
                {'id': discussion_instance.participant1_id, 'username': discussion_instance.participant1.username},
                {'id': discussion_instance.participant2_id, 'username': discussion_instance.participant2.username},
            ],
        }

    return JsonResponse(data)
