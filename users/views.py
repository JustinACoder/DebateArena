from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Model
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

from users.forms import ViewEditUserForm, ProfileForm


@login_required
def account_settings(request, tab='account'):
    context = {
        'profile_form': ProfileForm(instance=request.user.profile),
        'tab': tab,
    }

    return render(request, 'user/settings.html', context)


@login_required
@require_POST
def account_profile_edit(request, username):
    if username != request.user.username:
        return redirect('account_profile', username)

    profile_form = ProfileForm(request.POST, instance=request.user.profile)

    if profile_form.is_valid():
        profile_form.save()
        messages.success(request, 'Profile updated successfully')
    else:
        messages.error(request, 'Profile update failed')

    return redirect('account_settings', tab='profile')


def account_profile(request, username):
    # If the user comes from /profile/ without a username, it means they are not logged in
    if username == '':
        return redirect('account_login')

    # Get the user object for the profile
    profile_user = get_object_or_404(User.objects.select_related('profile'), username=username)

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
