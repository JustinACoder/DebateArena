from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.models import User
from discussion.models import Discussion
from users.forms import ViewEditUserForm


@login_required
def account_profile(request):
    # Get the user object
    user = request.user  # type: User

    # Get the list of pending discussion requests
    pending_requests = user.discussionrequest_set.select_related('debate').all()

    # Get the list of stances taken
    stances = user.stance_set.select_related('debate').all()

    # Get some stats
    # TODO: transform into a single query
    # - Number of stance taken
    # - Number of pending requests
    # - Number of conversations started
    # - Number of messages sent
    # - Number of comments posted
    stats = {
        'stance_count': stances.count(),
        'pending_request_count': pending_requests.count(),
        'discussion_count': Discussion.objects.filter(Q(participant1=user) | Q(participant2=user)).count(),
        'message_count': user.message_set.count(),
        'comment_count': user.comment_set.count(),
    }

    context = {
        'user_form': ViewEditUserForm(instance=user),
        'pending_requests': pending_requests,
        'stances': stances,
        'stats': stats,
    }

    return render(request, 'user/profile.html', context)
