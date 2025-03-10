from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import include, path, reverse
import debate.views
from debateme.urls import debate_urlpatterns as debateme_debate_urlpatterns

main_urlpatterns = [
    path('explore/', debate.views.explore, name='debate_explore'),
    path('search/', debate.views.search, name='debate_search'),
]

urlpatterns = [
    path('', lambda request: redirect('debate_explore')),
    path('<slug:debate_slug>/', include([
        path('', debate.views.debate, name='debate'),
        path('stance/', debate.views.set_stance, name='set_stance'),
        path('request_discussion/', debate.views.request_discussion, name='request_discussion'),
        path('vote/', debate.views.vote, name='vote'),
        path('comment/', debate.views.comment, name='comment'),
        path('list_comments/', debate.views.list_comments, name='list_comments'),
    ] + debateme_debate_urlpatterns)),  # TODO: figure out a better way to manage these URLs...
]
