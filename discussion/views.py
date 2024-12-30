from datetime import timedelta, datetime

from django.core.paginator import Paginator
from django.db.models import Q, F, BooleanField, When, Case, Value, Window, DateTimeField, Subquery, OuterRef
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Greatest
from django.db.models.functions.window import Lag
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ProjectOpenDebate.common.decorators import login_required_htmx
from discussion.forms import MessageForm
from discussion.models import Discussion, Message, ReadCheckpoint
from django.http import HttpResponseForbidden, HttpResponseNotFound


def set_message_additional_fields(*messages):
    """
    Adds additional fields to the messages. The additional fields are:
    - first_of_group: A boolean indicating whether the message is the first message in a group of messages that were
        sent within a 20-minute window.
    - formatted_datetime: A string representing the formatted datetime of the message. The format is as follows:
        - If the message was sent today, the time will be shown: "hh:mm"
        - If the message was sent in the last 6 days, the day of the week will be shown: "Mon hh:mm"
        - Otherwise, the full date will be shown: "Apr 1, 2021 hh:mm"

    Note: If messages is a queryset, it will be evaluated by calling this function

    :param messages: Message instances
    :return: None
    """
    # TODO: ensure that the timezone is correct
    current_date = datetime.now().date()
    twenty_minutes = timedelta(minutes=20)

    for message in messages:
        # Set the first_of_group flag
        message.first_of_group = message.prev_message_created_at is None or message.created_at - message.prev_message_created_at > twenty_minutes

        # Set the formatted datetime
        message_date = message.created_at.date()
        if message_date == current_date:
            message.formatted_datetime = message.created_at.strftime('%H:%M')
        elif current_date - timedelta(days=6) < message_date:
            message.formatted_datetime = message.created_at.strftime('%a %H:%M')
        else:
            message.formatted_datetime = message.created_at.strftime('%b %d, %Y %H:%M')


def get_most_recent_discussions_queryset(user, discussions_type='all'):
    """
    Get a queryset with the most recent discussions for the user. A discussion datetime is the maximum datetime
    between the discussion creation datetime and the most recent message datetime if the discussion has messages.

    :param user: User instance
    :param discussions_type: 'all', 'active' or 'archived' to filter the discussions accordingly
    :return: Queryset of discussions with the most recent datetime
    """
    # Both of the subqueries should be fast since they are indexed
    latest_message = Message.objects.filter(discussion=OuterRef('pk')).order_by('-created_at')[:1]
    readcheckpoint = ReadCheckpoint.objects.filter(discussion=OuterRef('pk'), user=user)[:1]

    # Filter the discussions based on the type
    if discussions_type == 'active':
        discussions_filter = ((Q(is_archived_for_p1=False) & Q(participant1=user)) |
                              Q(is_archived_for_p2=False) & Q(participant2=user))
    elif discussions_type == 'archived':
        discussions_filter = ((Q(is_archived_for_p1=True) & Q(participant1=user)) |
                              Q(is_archived_for_p2=True) & Q(participant2=user))
    elif discussions_type == 'all':
        discussions_filter = Q()
    else:
        return Discussion.objects.none()

    return Discussion.objects.filter(
        Q(participant1=user) | Q(participant2=user),
        discussions_filter
    ).annotate(
        latest_message_text=Subquery(latest_message.values('text')),
        latest_message_created_at=Subquery(latest_message.values('created_at')),
        latest_message_author=Subquery(latest_message.values('author__username')),
    ).annotate(
        recent_date=Greatest(
            'created_at',
            F('latest_message_created_at')
        ),
        # Check if the latest message is the same message pointed by the current user's readcheckpoint for the discussion
        has_unread_messages=Case(
            When(
                latest_message_created_at__gt=Subquery(
                    readcheckpoint.values('last_message_read__created_at')
                ),
                then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    ).select_related('debate', 'inviteuse').order_by('-recent_date')


@login_required
def discussion_default(request):
    # Get the most recent active discussion
    most_recent_discussion = get_most_recent_discussions_queryset(request.user, 'active').first()

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

    # Determine if the discussion is archived for the current user
    is_archived_for_current_user = Discussion.objects.get(pk=discussion_id).is_archived_for(request.user)

    context = {
        'message_form': MessageForm(),
        'is_archived_for_current_user': is_archived_for_current_user,
        'discussion_id': discussion_id
    }

    return render(request, 'discussion/discussion_board.html', context=context)


@login_required_htmx
def get_discussion_page(request):
    discussions_tab = request.GET.get('tab', 'active').lower()
    discussions_queryset = get_most_recent_discussions_queryset(request.user, discussions_tab)

    # Get the page
    paginator = Paginator(discussions_queryset, 15)
    page = paginator.get_page(request.GET.get('page', '1'))

    return render(request, 'discussion/discussion_list_page.html', {'page': page, 'tab': discussions_tab})


@login_required_htmx
def get_current_chat_page(request, discussion_id):
    # Get the discussion
    discussion_instance = get_object_or_404(
        Discussion.objects  # TODO: should we return 403 if the user is not a participant?
        .filter(Q(participant1=request.user) | Q(participant2=request.user))
        .prefetch_related('message_set', 'readcheckpoint_set')
        .select_related('debate', 'participant1', 'participant2'), pk=discussion_id)

    # Check if the conversation should be marked as archived for the current user
    is_archived_for_current_user = discussion_instance.is_archived_for(request.user)

    # Get the read checkpoint for the other user (we want to see which messages they have read)
    # We don't have to check for None since it is guaranteed that there is a read checkpoint for the other user
    read_checkpoint = discussion_instance.readcheckpoint_set.exclude(user=request.user).first()

    # Get the messages
    messages = discussion_instance.message_set.order_by('-created_at').annotate(
        is_current_user=Case(
            When(author=request.user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    # Add annotations for detecting group changes based on time differences
    messages = messages.annotate(
        # Get the timestamp of the previous message in the window
        prev_message_created_at=Window(
            expression=Lag('created_at', offset=1),
            order_by=F('created_at').asc(),
            output_field=DateTimeField()
        )
    )

    # Create the paginator
    paginator = Paginator(messages, 30)
    page = paginator.get_page(request.GET.get('page', '1'))

    # Add the additional fields (first_of_group, formatted_datetime) to the messages
    # This will be used to add time separators in the chat
    # TODO: should we do this on client side somehow? Or is there a cleaner way?
    #       This logic is also weirdly replicated in the consumer
    set_message_additional_fields(*page.object_list)

    context = {
        'page': page,
        'discussion': discussion_instance,
        'is_archived_for_current_user': is_archived_for_current_user,
        'read_checkpoint': read_checkpoint,
    }

    return render(request, 'discussion/current_chat_page.html', context)


@login_required_htmx
def get_single_discussion(request):
    # Get the discussion id
    discussion_id = request.GET.get('discussion_id')

    # Get the discussion (active or archived)
    discussion_instance = get_most_recent_discussions_queryset(request.user).filter(pk=discussion_id).first()

    if discussion_instance is None:
        return HttpResponseNotFound()

    return render(request, 'discussion/discussion.html', {'discussion': discussion_instance})


@login_required
@require_POST
def set_archive_status(request, discussion_id):
    # Get the discussion
    discussion_instance = get_object_or_404(
        Discussion.objects.filter(Q(participant1=request.user) | Q(participant2=request.user)), pk=discussion_id)

    # Get the archive status
    archive_status = request.POST.get('status', 'true').lower() == 'true'

    # Set the archive status
    if request.user == discussion_instance.participant1:
        discussion_instance.is_archived_for_p1 = archive_status
    else:
        discussion_instance.is_archived_for_p2 = archive_status

    discussion_instance.save()

    # Redirect to the discussion that we have just archived
    return redirect('specific_discussion', discussion_id=discussion_id)


def create_discussion_and_readcheckpoints(debate, participant1, participant2):
    """
    Create a discussion between the two participants and create ReadCheckpoints for both participants.

    :param debate: The debate for the discussion (Debate instance or id)
    :param participant1: The first participant (User instance or id)
    :param participant2: The second participant (User instance or id)
    :return: The created discussion instance
    """
    # Generate the args for the discussion
    # Add the _id suffix to the arguments to avoid unnecessary queries
    # if the parameters are ints (which represent the ids)
    args = {
        'debate': debate,
        'participant1': participant1,
        'participant2': participant2
    }
    for key, value in args.items():
        if isinstance(value, int):
            args[key] = value

    # Create a discussion
    discussion_instance = Discussion.objects.create(
        debate=debate,
        participant1=participant1,
        participant2=participant2
    )

    # Create ReadCheckpoints for both participants of the discussion
    discussion_instance.create_read_checkpoints()

    return discussion_instance


@login_required
def get_discussion_info(request, discussion_id):
    """
    Get information on the discussion to be displayed to the user upon request.
    The info returned includes:
    - Debate object
    - The participants and their stance
    - The number of messages in the discussion
    - Discussion object
    - Origin of the discussion (through an invitation or the platform matchmaking)
    - Whether the discussion is archived for the current user

    :param discussion_id: The id of the discussion to get information about
    :param request: The request object
    :return: The rendered response
    """
    # Get the discussion
    discussion_instance = get_object_or_404(
        Discussion.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        ).select_related('participant1', 'participant2', 'debate', 'inviteuse'), pk=discussion_id)

    # Get the debate
    debate_instance = discussion_instance.debate

    # Get the participants and their stance
    if request.user == discussion_instance.participant1:
        current_user = discussion_instance.participant1
        other_user = discussion_instance.participant2
    else:
        current_user = discussion_instance.participant2
        other_user = discussion_instance.participant1
    current_user.stance = debate_instance.get_stance(current_user)
    other_user.stance = debate_instance.get_stance(other_user)

    # Get the number of messages in the discussion
    message_count = discussion_instance.message_set.count()

    # Get the origin of the discussion
    invite_instance = discussion_instance.inviteuse.invite if discussion_instance.is_from_invite else None

    # Check if the conversation should be marked as archived for the current user
    is_archived_for_current_user = discussion_instance.is_archived_for(request.user)

    context = {
        'message_count': message_count,
        'discussion': discussion_instance,
        'current_user': current_user,
        'other_user': other_user,
        'invite': invite_instance,
        'is_archived_for_current_user': is_archived_for_current_user
    }

    return render(request, 'discussion/discussion_info.html', context)
