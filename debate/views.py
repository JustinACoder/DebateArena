from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, Subquery, F, Exists, Count, Case, When
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed, \
    JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from voting.models import Vote

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
    debate_instance = get_object_or_404(Debate.objects.select_related('author'), title=debate_title)

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
                # TODO: this is a anti-pattern
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

    # Get the user's stance on the debate
    # Note we check using the user_id instead of user since it could be AnonymousUser (not authenticated)
    user_stance = Stance.objects.filter(user_id=request.user.id, debate=debate_instance).first()

    # Get the user's discussion requests on the debate
    # Note we check using the user_id instead of user since it could be AnonymousUser (not authenticated)
    user_discussion_requests = DiscussionRequest.objects.filter(requester_id=request.user.id, debate=debate_instance)
    has_requested_for = user_discussion_requests.filter(stance_wanted=True).exists()
    has_requested_against = user_discussion_requests.filter(stance_wanted=False).exists()

    # Get all comments for the debate sorted by date
    comments = debate_instance.comment_set.order_by('date_added').select_related('author')

    # Get the user's vote on the debate
    debate_vote = Vote.objects.get_for_user(debate_instance, request.user)

    # Get votes for the comments
    comment_votes = Vote.objects.get_for_user_in_bulk(comments, request.user)

    # Get the score for the debate
    debate_score = Vote.objects.get_score(debate_instance)

    # Get the number of votes for each comment
    comment_vote_scores = Vote.objects.get_scores_in_bulk(comments)

    # Annotate the debate with the user's stance, discussion requests and vote
    debate_instance.vote = debate_vote
    debate_instance.vote_score, debate_instance.num_votes = debate_score['score'], debate_score['num_votes']

    # Annotate the comments with the vote information
    for comment in comments:
        key = str(comment.id)
        comment.vote = comment_votes.get(key)
        comment.vote_score, comment.num_votes = comment_vote_scores.get(key, {'score': 0, 'num_votes': 0}).values()

    # Define the context to be passed to the template
    context = {
        'debate': debate_instance,
        'stance': user_stance,
        'has_requested_for': has_requested_for,
        'has_requested_against': has_requested_against,
        'comments': comments,
        'comment_form': comment_form
    }

    return render(request, 'debate/debate.html', context)


@login_required
@require_POST
def set_stance(request, debate_title):
    debate_instance = get_object_or_404(Debate, title=debate_title)

    # Check that the request contains the necessary data
    stance = request.POST.get('stance')
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
    stance_wanted = request.GET.get('stance_wanted')
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
    # TODO: make modal instead? Also, is this really a success message?
    messages.success(request,
                     "No user is currently available for a discussion on this debate. Once a user is available, a new discussion will be created and you will be notified.")

    # Redirect to the debate page
    return redirect(debate, debate_title)


@login_required
@require_POST
def vote(request, debate_title):
    debate_instance = get_object_or_404(Debate, title=debate_title)

    # Ensure that the direction is present and valid
    direction = request.POST.get('direction')
    if direction not in ['-1', '0', '1']:
        return HttpResponseBadRequest()
    direction = int(direction)

    # Check if the user tries to vote on a comment or the debate itself
    if 'comment_id' in request.POST:
        instance_to_vote_on = get_object_or_404(debate_instance.comment_set, id=request.POST['comment_id'])
    else:
        instance_to_vote_on = debate_instance

    # Record the vote
    Vote.objects.record_vote(instance_to_vote_on, request.user, direction)

    # Get the new score of the instance
    new_score_dict = Vote.objects.get_score(instance_to_vote_on)

    # Return the new score
    return JsonResponse(new_score_dict)


