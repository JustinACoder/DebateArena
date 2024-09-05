from django.core.paginator import Paginator
from django.db.models import Q, F, BooleanField, When, Case, Value, Max
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Greatest
from django.shortcuts import render, get_object_or_404, redirect

from ProjectOpenDebate.common.decorators import login_required_htmx
from debate.models import Debate
from discussion.forms import MessageForm
from discussion.models import Discussion, Message
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseNotFound


def get_most_recent_discussions_queryset(user):
    """
    Get a queryset with the most recent discussions for the user. A discussion datetime is the maximum datetime
    between the discussion creation datetime and the most recent message datetime if the discussion has messages.

    :param user: User instance
    :return: Queryset of discussions with the most recent datetime
    """
    # TODO: denormalize the db by adding a latest_message one-to-one field to Discussion for large scale
    # OR even better, we can create a composite index on (discussion_id, created_at) for the message table
    # and then use a subquery to get the latest message for each discussion
    # This would result in a simpler, highly optimized query that works very well with the ORM
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

    if most_recent_discussion:
        return redirect('specific_discussion', discussion_id=most_recent_discussion.id)
    else:
        return render(request, 'discussion/discussion_board.html',
                      {'message_form': MessageForm(), 'discussion_id': None})


@login_required
def specific_discussion(request, discussion_id):
    # If the current user is not a participant in the discussion, return 403
    if not Discussion.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user), pk=discussion_id).exists():
        return HttpResponseForbidden()

    context = {
        'message_form': MessageForm(),
        'discussion_id': discussion_id
    }

    return render(request, 'discussion/discussion_board.html', context=context)


@login_required_htmx
def get_discussion_page(request):
    discussions_queryset = get_most_recent_discussions_queryset(request.user)

    # Get the page
    paginator = Paginator(discussions_queryset, 15)
    page = paginator.get_page(request.GET.get('page', '1'))

    return render(request, 'discussion/discussion_list_page.html', {'page': page})


@login_required_htmx
def get_current_chat_page(request, discussion_id):
    # Get the discussion
    discussion_instance = get_object_or_404(
        Discussion.objects  # TODO: should we return 403 if the user is not a participant?
        .filter(Q(participant1=request.user) | Q(participant2=request.user))
        .prefetch_related('message_set')
        .select_related('debate', 'participant1', 'participant2'), pk=discussion_id)

    # Get the messages
    messages = discussion_instance.message_set.order_by('-created_at').annotate(
        is_current_user=Case(
            When(author=request.user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    # Create the paginator
    paginator = Paginator(messages, 30)
    page = paginator.get_page(request.GET.get('page', '1'))

    return render(request, 'discussion/current_chat_page.html', {'page': page, 'discussion': discussion_instance})


@login_required_htmx
def get_single_discussion(request):
    # Get the discussion id
    discussion_id = request.GET.get('discussion_id')

    # Get the discussion
    discussion_instance = get_most_recent_discussions_queryset(request.user).filter(pk=discussion_id).first()

    if discussion_instance is None:
        return HttpResponseNotFound()

    return render(request, 'discussion/discussion.html', {'discussion': discussion_instance})
