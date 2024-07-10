from django.urls import include, path, reverse
import debateme.views

accounts_urlpatterns = [
    path('invitations/', debateme.views.list_invites, name='list_invites'),
]

debate_urlpatterns = [
    path('create/', debateme.views.create_invite, name='create_invite'),
]

urlpatterns = [
    path('<str:invite_code>/', include(
        [
            path('', debateme.views.view_invite, name='view_invite'),
            path('delete/', debateme.views.delete_invite, name='delete_invite'),
            path('accept/', debateme.views.accept_invite, name='accept_invite'),
        ]
    )),
]
