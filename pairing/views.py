from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from debate.models import Debate
from pairing.models import PairingRequest


@login_required
@require_POST
def request_passive_pairing(request, debate_id):
    """Request passive pairing for the current user."""
    stance_wanted = request.POST.get('stance_wanted') == 'for'
    debate = get_object_or_404(Debate, id=debate_id)

    # Check if the user already has a similar pairing request
    if request.user.pairingrequest_set.filter(
            debate=debate,
            status=PairingRequest.Status.PASSIVE,
            desired_stance=stance_wanted
    ).exists():
        messages.error(request, "You already have a similar pairing request.")
        return redirect('debate', debate.slug)

    # Create the pairing request
    PairingRequest.objects.create(
        user=request.user,
        debate=debate,
        status=PairingRequest.Status.PASSIVE,
        desired_stance=stance_wanted
    )

    messages.success(request, "Passive pairing request created. You will be notified when a match is found.")
    return redirect('debate', debate.slug)
