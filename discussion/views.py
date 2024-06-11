from django.contrib.auth.models import User
from django.db.models import Q, Window, F, BooleanField, When, Case, Value, TextField, OuterRef, Subquery
from django.contrib.auth.decorators import login_required
from django.db.models.functions import FirstValue, Coalesce
from django.shortcuts import render, get_object_or_404, redirect
from django.db import connection

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


@login_required
def discussion_default(request):
    # Get the most recent discussion for the current user
    # most_recent_discussion_id = (Message.objects.filter(
    #     Q(discussion__participant1=request.user) | Q(discussion__participant2=request.user)
    # ).order_by('-created_at').values_list('discussion_id', flat=True).first())
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT dd.id
            FROM discussion_discussion dd
                     LEFT JOIN discussion_message dm ON dd.id = dm.discussion_id
            WHERE dd.participant1_id = %s OR dd.participant2_id = %s
            ORDER BY COALESCE(dm.created_at, dd.created_at) DESC
            LIMIT 1;
            """,
            [request.user.id, request.user.id]
        )
        result = cursor.fetchone()
        most_recent_discussion_id = result[0] if result else None

    return specific_discussion(request, most_recent_discussion_id)


@login_required
def specific_discussion(request, discussion_id):
    # The problem with the orm query is that I can't find a clear AND efficient way of getting both
    # the conversations with and without messages with the rest of the information.
    # The commented out orm query below is the closest I got. It retrieves all discussions with the most recent
    # message, but it doesn't retrieve discussions without messages.
    # I tried using union, but it doesn't work well since it changes the order of the fields.
    # discussions_info = (
    #     Message.objects.filter(
    #         Q(discussion__participant1=request.user) | Q(discussion__participant2=request.user)
    #     ).annotate(
    #         latest_message=Window(
    #             expression=FirstValue('id'),
    #             partition_by=[F('discussion_id')],
    #             order_by=['-created_at']
    #         )
    #     ).filter(
    #         latest_message=F('id')
    #     ).values(
    #         'discussion_id', 'discussion__debate__title', 'discussion__participant1__username',
    #         'discussion__participant2__username', 'text', 'created_at'
    #     ).order_by('-created_at')
    # )

    # Get discussions with the most recent message or without messages
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM (SELECT dd.id                                                                               as discussion_id,
                         dd.debate_id                                                                        as debate_id,
                         db.title                                                                            as debate_title,
                         dd.created_at                                                                       as discussion_created_at,
                         dm.id                                                                               as message_id,
                         dm.text                                                                             as message_text,
                         dm.created_at                                                                       as message_created_at,
                         p1.username                                                                         as participant1_username,
                         p2.username                                                                         as participant2_username,
                         p1.id                                                                               as participant1_id,
                         p2.id                                                                               as participant2_id,
                         FIRST_VALUE(dm.id) OVER (PARTITION BY dm.discussion_id ORDER BY dm.created_at DESC) as first_message_id,
                         COALESCE(dm.created_at, dd.created_at)                                              as latest_activity_at
                  FROM discussion_discussion dd
                           JOIN auth_user p1 ON dd.participant1_id = p1.id
                           JOIN auth_user p2 ON dd.participant2_id = p2.id
                           LEFT JOIN discussion_message dm ON dd.id = dm.discussion_id
                           JOIN debate_debate db ON dd.debate_id = db.id
                  WHERE (dd.participant1_id = %s OR dd.participant2_id = %s)) as sub
            WHERE message_id = first_message_id
               OR first_message_id IS NULL
            ORDER BY latest_activity_at DESC;
            """,
            [request.user.id, request.user.id]
        )
        discussions_info = dictfetchall(cursor)

    # If this view is called with a discussion_id but the query is empty, it means that the discussion doesn't exist
    # OR the user is not a participant. Therefore, we will redirect to the default discussion view.
    if not discussions_info and discussion_id:
        return redirect(discussion_default)  # TODO: should we return an error instead?

    # Get Message form
    message_form = MessageForm()

    # Create context
    context = {
        'discussions_info': discussions_info,
        'message_form': message_form,
        'discussion_id': discussion_id,
        'remove_footer': True
    }

    return render(request, 'discussion/discussion_board.html', context=context)


@login_required
def retrieve_messages(request, discussion_id):
    discussion_instance = get_object_or_404(Discussion.objects  # TODO: should we return 403 if the user is not a participant?
                           .filter(Q(participant1=request.user) | Q(participant2=request.user))
                           .prefetch_related('message_set')
                           .select_related('debate', 'participant1', 'participant2'), pk=discussion_id)
    messages = discussion_instance.message_set.order_by('created_at').annotate(
        is_current_user=Case(
            When(author=request.user, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).values('id', 'author__username', 'text', 'created_at', 'is_current_user')

    data = {
        'discussion': {
            'id': discussion_instance.id,
            'debate': discussion_instance.debate.title,
            'participants': [
                {'id': discussion_instance.participant1_id, 'username': discussion_instance.participant1.username},
                {'id': discussion_instance.participant2_id, 'username': discussion_instance.participant2.username},
            ],
        },
        'messages': list(messages)
    }

    return JsonResponse(data, safe=False)
