from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from discussion.models import Discussion
from users.forms import ViewEditUserForm
from allauth.account.views import EmailView


@login_required
def account_settings(request):
    # Get the user object
    user = request.user  # type: User

    return render(request, 'user/settings.html')


def account_profile(request, username):
    # If the user comes from /profile/ without a username, it means they are not logged in
    if username == '':
        return redirect('account_login')

    # Get the user object for the profile
    profile_user = get_object_or_404(User, username=username)

    # Get the list of pending discussion requests
    pending_requests = profile_user.discussionrequest_set.select_related('debate').all()

    # Get the list of stances taken
    stances = profile_user.stance_set.select_related('debate').all()

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
        'discussion_count': Discussion.objects.filter(
            Q(participant1=profile_user) | Q(participant2=profile_user)).count(),
        'message_count': profile_user.message_set.count(),
        'comment_count': profile_user.comment_set.count(),
    }

    context = {
        'profile_user': profile_user,
        'pending_requests': pending_requests,
        'stances': stances,
        'stats': stats,
    }

    return render(request, 'user/profile.html', context)
