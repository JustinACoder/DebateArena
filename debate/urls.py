from django.http import HttpResponseRedirect
from django.urls import include, path, reverse, re_path
from voting.views import xmlhttprequest_vote_on_object

import debate.views

urlpatterns = [
    path('', debate.views.index, name='debate_index'),
    path('<slug:debate_slug>/', debate.views.debate, name='debate'),
    path('<slug:debate_slug>/stance/', debate.views.set_stance, name='set_stance'),
    path('<slug:debate_slug>/request_discussion/', debate.views.request_discussion, name='request_discussion'),
    path('<slug:debate_slug>/vote/', debate.views.vote, name='vote'),
]