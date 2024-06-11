from django.http import HttpResponseRedirect
from django.urls import include, path, reverse, re_path
from voting.views import xmlhttprequest_vote_on_object

import debate.views

urlpatterns = [
    path('', debate.views.index, name='debate_index'),
    path('<str:debate_title>/', debate.views.debate, name='debate'),
    path('<str:debate_title>/stance/', debate.views.set_stance, name='set_stance'),
    path('<str:debate_title>/request_discussion/', debate.views.request_discussion, name='request_discussion'),
    path('<str:debate_title>/vote/', debate.views.vote, name='vote'),
]