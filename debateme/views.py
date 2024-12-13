from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from debate.models import Debate
from debateme.models import Invite, InviteUse
from discussion.models import Discussion
from discussion.views import initialize_discussion
from notifications.models import Notification


def view_invite(request, invite_code):
    try:
        invite = Invite.objects.select_related('debate', 'creator').get(code=invite_code)
    except Invite.DoesNotExist:
        return render(request, 'debateme/invite_not_found.html', status=404)

    return render(request, 'debateme/view_invite.html', {'invite': invite})


@require_POST
@login_required
def delete_invite(request, invite_code):
    try:
        invite = Invite.objects.get(code=invite_code, creator=request.user)
    except Invite.DoesNotExist:
        return HttpResponseNotFound()

    invite.delete()

    messages.success(request, f"Invitation deleted successfully.")

    return redirect('list_invites')


@require_POST
@login_required
def accept_invite(request, invite_code):
    try:
        invite = Invite.objects.get(code=invite_code)
    except Invite.DoesNotExist:
        return HttpResponseNotFound()

    # If the user attempting to accept the invite is the creator of the invite, they should not be able to accept it.
    # However, we do not need to make it fail prettily, as the frontend should not allow this to happen.
    # Therefore, we can just return a 403 Forbidden.
    if invite.creator == request.user:
        return HttpResponseForbidden()

    # If the user has already used the invite, redirect them to the discussion
    try:
        existing_discussion_id = invite.inviteuse_set.get(user=request.user).resulting_discussion_id

        messages.info(request, f"Invitation already accepted. Redirected to existing debate.")

        return redirect('specific_discussion', discussion_id=existing_discussion_id)
    except InviteUse.DoesNotExist:
        pass

    # Create a new discussion and invite use
    participant1, participant2 = invite.creator, request.user
    discussion = initialize_discussion(invite.debate, participant1, participant2)

    # Create an InviteUse object to mark that the invite has been used
    invite_use = InviteUse.objects.create(invite=invite, user=request.user, resulting_discussion=discussion)

    # Create a notification for the creator of the invite
    Notification.objects.create_accepted_invite_notification(invite, invite_use, request.user)

    messages.success(request, f"Debate started successfully.")

    return redirect('specific_discussion', discussion_id=discussion.id)


@login_required
def list_invites(request):
    # Get all invites created by the user and related information such as the number of uses (foreign key from InviteUse to Invite)
    invites = Invite.objects.filter(
        creator=request.user
    ).select_related('debate').annotate(
        num_uses=Count('inviteuse')
    ).order_by('-created_at')

    return render(request, 'debateme/list_invites.html', {'invites': invites})


@login_required
@require_POST
def create_invite(request, debate_slug):
    debate = get_object_or_404(Debate, slug=debate_slug)

    invite = Invite.objects.create(creator=request.user, debate=debate)

    messages.success(request, f"Invite created successfully.")

    return redirect(invite)