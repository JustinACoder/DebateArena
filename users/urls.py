from django.urls import path
from django.contrib.auth import views as auth_views
import users.views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='user_login'),
    path('register/', users.views.user_register, name='user_register'),
    path('logout/', auth_views.LogoutView.as_view(), name='user_logout'),
]
