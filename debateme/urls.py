from django.urls import include, path, reverse
import debateme.views

urlpatterns = [
    path('<str:invite_code>/', include(
        [
            path('', debateme.views.view_invite, name='view_invite'),
            path('delete/', debateme.views.delete_invite, name='delete_invite'),
            path('accept/', debateme.views.accept_invite, name='accept_invite'),
        ]
    )),
]
