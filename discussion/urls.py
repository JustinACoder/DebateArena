from django.urls import include, path, reverse
import discussion.views

urlpatterns = [
    path('', discussion.views.discussion_default, name='discussion_default'),
    path('<int:discussion_id>/', discussion.views.specific_discussion, name='specific_discussion'),
    path('<int:discussion_id>/messages/', discussion.views.get_current_chat_page, name='get_current_chat_page'),
    path('page/', discussion.views.get_discussion_page, name='get_discussion_page'),
    path('get_discussion/', discussion.views.get_single_discussion, name='get_single_discussion'),
]
