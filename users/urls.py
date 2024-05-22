from django.urls import path
from django.contrib.auth.views import LoginView, PasswordResetView
import users.views

urlpatterns = [
    path('login/', LoginView.as_view(redirect_authenticated_user=True), name='user_login'),
    path('register/', users.views.user_register, name='user_register'),
    path('logout/', users.views.user_logout, name='user_logout'),
    path('profile/', users.views.user_profile, name='user_profile'),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
]
