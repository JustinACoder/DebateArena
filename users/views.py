from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from discussion.models import Discussion
from users.forms import ViewEditUserForm
from allauth.account.views import EmailView


@login_required
def account_settings(request):
    return render(request, 'user/settings.html')


def account_profile(request, username):
    # If the user comes from /profile/ without a username, it means they are not logged in
    if username == '':
        return redirect('account_login')

    # Get the user object for the profile
    profile_user = get_object_or_404(User, username=username)

    # Get recent stances
    stances = profile_user.stance_set.order_by('-created_at')[:10]

    context = {
        'profile_user': profile_user,
        'recent_stances': stances,
    }

    return render(request, 'user/profile.html', context)


@login_required
def account_profile_default(request):
    return redirect('account_profile', username=request.user.username)