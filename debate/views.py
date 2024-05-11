from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from .forms import CommentForm
from .models import Debate, Comment
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
