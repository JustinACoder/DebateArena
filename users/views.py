from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm


def user_register(request):
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
