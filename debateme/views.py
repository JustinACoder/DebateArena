from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from debateme.models import Invite, InviteUse
from discussion.models import Discussion


def invite_not_found(request):
    return render(request, 'debateme/invite_not_found.html')


def view_invite(request, invite_code):
    try:
        invite = Invite.objects.select_related('debate', 'creator').get(code=invite_code)
    except Invite.DoesNotExist:
        return redirect('invite_not_found')

    return render(request, 'debateme/view_invite.html', {'invite': invite})


@require_POST
@login_required
def delete_invite(request, invite_code):
    try:
        invite = Invite.objects.get(code=invite_code, creator=request.user)
    except Invite.DoesNotExist:
        return HttpResponseNotFound()

    invite.delete()
    return HttpResponse(status=204)


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
        return redirect(reverse('discussion', args=[existing_discussion_id]))
    except InviteUse.DoesNotExist:
        pass

    # Create a new discussion and invite use
    discussion = Discussion.objects.create(debate=invite.debate, participant1=invite.creator, participant2=request.user)
    InviteUse.objects.create(invite=invite, user=request.user, resulting_discussion=discussion)

    # Notify the participants of the new discussion
    discussion.notify_participants()

    return redirect('specific_discussion', discussion_id=discussion.id)

