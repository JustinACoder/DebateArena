from django.urls import include, path, reverse
import discussion.views

urlpatterns = [
    path('', discussion.views.discussion_default, name='discussion_default'),
    path('<int:discussion_id>/', discussion.views.specific_discussion, name='specific_discussion'),
    path('<int:discussion_id>/messages/', discussion.views.retrieve_messages, name='retrieve_messages'),
]
