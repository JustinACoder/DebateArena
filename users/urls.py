from django.urls import path
from django.contrib.auth.views import LoginView, PasswordResetView
import users.views

urlpatterns = [
    path('profile/', users.views.account_settings, name='account_settings'),
]
