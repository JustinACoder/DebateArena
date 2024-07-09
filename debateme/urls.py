from django.urls import include, path, reverse
import debateme.views

urlpatterns = [
    path('invite_not_found/', debateme.views.invite_not_found, name='invite_not_found'),
    path('<str:invite_code>/', debateme.views.view_invite, name='view_invite'),
    path('<str:invite_code>/delete/', debateme.views.delete_invite, name='delete_invite'),
    path('<str:invite_code>/accept/', debateme.views.accept_invite, name='accept_invite'),
]
