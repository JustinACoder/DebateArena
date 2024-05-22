from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, Subquery, F, Exists
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed, \
    JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from discussion.models import DiscussionRequest, Discussion
from discussion.views import specific_discussion
from .forms import CommentForm
from .models import Debate, Comment, Stance
import logging

logger = logging.getLogger(__name__)


def index(request):
    debates = Debate.objects.all()
    return render(request, 'debate/index.html', {'debates': debates})


def debate(request, debate_title):
    debate_query = Debate.objects.select_related('author').annotate(
        user_stance=Subquery(
            Stance.objects.filter(user=request.user, debate=OuterRef('pk')).values('stance')[:1]
        ),
        has_requested_for=Exists(
            DiscussionRequest.objects.filter(
                requester=request.user,
                debate=OuterRef('pk'),
                stance_wanted=True
            )
        ),
        has_requested_against=Exists(
            DiscussionRequest.objects.filter(
                requester=request.user,
                debate=OuterRef('pk'),
                stance_wanted=False
            )
        )
    ).prefetch_related('comment_set', 'comment_set__author')

    debate_instance = get_object_or_404(debate_query, title=debate_title)

    # If the request is a POST request, there is an action to be performed
    if request.method == 'POST':
        if 'action' not in request.POST:
            return HttpResponseBadRequest()

        # Depending on the action, perform the appropriate action
        if request.POST['action'] == 'add_comment':
            # Check that the user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden()

            # Create a comment using the form data
            comment_form = CommentForm(request.POST)

            # Save the comment to the database if the form is valid
            if comment_form.is_valid():
                comment_instance = comment_form.save(commit=False)
                comment_instance.debate = debate_instance
                comment_instance.author = request.user
                comment_instance.save()

                # Redirect to the same page to avoid resubmission of the form
                return HttpResponseRedirect(request.path_info)
        else:
            # If the action is not recognized, return an error
            return HttpResponseBadRequest()
    else:
        comment_form = CommentForm()

    # Get all comments for the debate sorted by date
    comments = (debate_instance.comment_set
                .order_by('date_added')
                .select_related('author'))

    # Define the context to be passed to the template
    context = {
        'debate': debate_instance,
        'comments': comments,
        'comment_form': comment_form
    }

    return render(request, 'debate/debate.html', context)


@login_required
@require_POST
def set_stance(request, debate_title):
    debate_instance = get_object_or_404(Debate, title=debate_title)

    # Check that the request contains the necessary data
    stance = request.POST.get('stance', None)
    if stance not in ['for', 'against', 'reset']:
        return HttpResponseBadRequest()

    # Update the user's stance on the debate
    if stance == 'reset':
        debate_instance.stance_set.filter(user=request.user).delete()
    else:
        stance_bool = stance == 'for'
        debate_instance.stance_set.update_or_create(user=request.user, defaults={'stance': stance_bool})

    # Delete any pending discussion requests for the user on this debate
    DiscussionRequest.objects.filter(requester=request.user, debate=debate_instance).delete()

    return HttpResponse(status=204)


@login_required
def request_discussion(request, debate_title):
    # Check that the wanted stance is valid
    stance_wanted = request.GET.get('stance_wanted', None)
    if stance_wanted not in ['for', 'against']:
        return HttpResponseBadRequest()
    stance_wanted_bool = stance_wanted == 'for'

    # Get or 404 the debate instance
    debate_instance = get_object_or_404(Debate, title=debate_title)

    # Get the user's stance on the debate
    user_stance = debate_instance.stance_set.filter(user=request.user).first()

    # If the user did not set a stance, return an error
    if not user_stance:
        return HttpResponseForbidden()

    # If the user has already a similar request pending, return an error
    similar_request_exists = DiscussionRequest.objects.filter(
        requester=request.user,
        stance_wanted=stance_wanted_bool,
        debate=debate_instance
    ).exists()
    if similar_request_exists:
        return HttpResponseForbidden()

    # Check if it is possible to fill another request using this new request
    matching_discussion_requests = DiscussionRequest.objects.exclude(
        requester=request.user  # Exclude the user's own requests
    ).filter(
        debate=debate_instance,  # Limit to the debate of the request
        requester__stance__stance=stance_wanted_bool,  # Limit to requester with the wanted stance
        requester__stance__debate=debate_instance  # Make sure we join on the stances for the debate instance
    ).annotate(
        requester_stance=F('requester__stance__stance')  # Get the stance of the requester
    ).filter(
        stance_wanted=user_stance.stance  # Limit to requests where the wanted stance matches the requester's stance
    ).order_by('created_at')

    # If there is a matching request, create a discussion and delete the requests
    # However, to prevent two users from reading the same request and creating two discussions,
    # we need to make the operation atomic.
    # We also want to minimize the atomic operation to only the necessary operations.
    with transaction.atomic():
        earliest_matching_discussion_request = matching_discussion_requests.first()
        if earliest_matching_discussion_request:
            earliest_matching_discussion_request.delete()

    # If there was a matching request, create a discussion and return the discussion page
    if earliest_matching_discussion_request:
        # Create a discussion
        discussion_instance = Discussion.objects.create(
            debate=debate_instance,
            participant1=earliest_matching_discussion_request.requester,
            participant2=request.user
        )

        # Redirect to the discussion page
        return redirect(specific_discussion, discussion_instance.id)

    # Otherwise, create a new request and display the debate page
    DiscussionRequest.objects.create(
        requester=request.user,
        stance_wanted=stance_wanted_bool,
        debate=debate_instance
    )

    # Display a message to the user
    # TODO: make modal instead?
    messages.success(request,
                     "No user is currently available for a discussion on this debate. Once a user is available, a new discussion will be created and you will be notified.")

    # Redirect to the debate page
    return redirect(debate, debate_title)
