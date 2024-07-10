from django.http import HttpResponseRedirect
from django.urls import include, path, reverse, re_path
from voting.views import xmlhttprequest_vote_on_object

import debate.views
from debateme.urls import debate_urlpatterns as debateme_debate_urlpatterns

urlpatterns = [
    path('', debate.views.index, name='debate_index'),
    path('<slug:debate_slug>/', include([
        path('', debate.views.debate, name='debate'),
        path('stance/', debate.views.set_stance, name='set_stance'),
        path('request_discussion/', debate.views.request_discussion, name='request_discussion'),
        path('vote/', debate.views.vote, name='vote'),
    ] + debateme_debate_urlpatterns)),  # TODO: figure out a better way to manage these URLs...
]
