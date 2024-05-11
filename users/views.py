from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LogoutView
from django.contrib.auth.models import User


def user_register(request):
    if request.user.is_authenticated:
        return redirect('debate_index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()

            # redirect to login page
            messages.success(request, 'Account created successfully. Please login.')
            return redirect('user_login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def user_logout(request):
    messages.info(request, 'You have been logged out.')
    return LogoutView.as_view(next_page='user_login')(request)
