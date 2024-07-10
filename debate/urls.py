from django.urls import include, path
import debate.views
from debateme.urls import debate_urlpatterns as debateme_debate_urlpatterns

urlpatterns = [
    path('', debate.views.explore, name='debate_explore'),
    path('<slug:debate_slug>/', include([
        path('', debate.views.debate, name='debate'),
        path('stance/', debate.views.set_stance, name='set_stance'),
        path('request_discussion/', debate.views.request_discussion, name='request_discussion'),
        path('vote/', debate.views.vote, name='vote'),
    ] + debateme_debate_urlpatterns)),  # TODO: figure out a better way to manage these URLs...
]
