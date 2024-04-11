from django.http import HttpResponseRedirect
from django.urls import include, path, reverse
import debate.views

urlpatterns = [
    path('', debate.views.index, name='debate_index'),
    path('d/<str:debate_title>/', debate.views.debate, name='debate'),
    path('d/', lambda request: HttpResponseRedirect(reverse('debate_index')))

]