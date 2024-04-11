from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseRedirect
from .forms import ArgumentForm
from .models import Debate, Argument
import logging

logger = logging.getLogger(__name__)


def index(request):
    debates = Debate.objects.all()
    return render(request, 'debate/index.html', {'debates': debates})


def debate(request, debate_title):
    debate_instance = get_object_or_404(Debate, title=debate_title)
    argument_form = ArgumentForm()

    # If the request is a POST request, there is an action to be performed
    if request.method == 'POST':
        if 'action' not in request.POST:
            return HttpResponse("Missing action in POST request", status=400)

        # Depending on the action, perform the appropriate action
        if request.POST['action'] == 'add_argument':
            # Create an argument using the form data
            argument_form = ArgumentForm(request.POST)

            # Save the argument to the database if the form is valid
            if argument_form.is_valid():
                argument = argument_form.save(commit=False)
                argument.debate = debate_instance
                argument.save()

                # Redirect to the same page to avoid resubmission of the form
                return HttpResponseRedirect(request.path_info)
        else:
            # If the action is not recognized, return an error
            logger.warning("Invalid debate action in POST request: %s", request.POST['action'])
            return HttpResponse("Invalid debate action in POST request", status=400)

    # Get all arguments for the debate and order them by date in descending order
    arguments = debate_instance.argument_set.order_by('-date')

    # Define the context to be passed to the template
    context = {
        'debate': debate_instance,
        'arguments': arguments,
        'argument_form': argument_form
    }

    return render(request, 'debate/debate.html', context)
