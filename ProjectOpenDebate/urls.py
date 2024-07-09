"""
URL configuration for ProjectOpenDebate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path, reverse
from . import views
from debateme.urls import accounts_urlpatterns as debateme_accounts_urlpatterns


accounts_urlpatterns = [
    path('', include('allauth.urls')),
    path('', include('users.urls')),
] + debateme_accounts_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main, name='main'),
    path('d/', include('debate.urls')),
    path('accounts/', include(accounts_urlpatterns)),
    path('chat/', include('discussion.urls')),
    path('debateme/', include('debateme.urls')),
    path("__debug__/", include("debug_toolbar.urls")),
]
