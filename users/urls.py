from django.shortcuts import redirect
from django.urls import path
from django.contrib.auth.views import LoginView, PasswordResetView
import users.views

urlpatterns = [
    path('settings/', users.views.account_settings, name='account_settings'),
    path('profile/', lambda request: redirect('account_profile', request.user.username), name='account_profile'),
    path('profile/<str:username>/', users.views.account_profile, name='account_profile'),
]
