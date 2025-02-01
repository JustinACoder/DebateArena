from django.shortcuts import redirect
from django.urls import include, path

from pairing.views import request_passive_pairing

urlpatterns = [
    path('request_passive_pairing/<int:debate_id>/', request_passive_pairing, name='request_passive_pairing'),
]
