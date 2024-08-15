from django.urls import include, path, reverse
import notifications.views

urlpatterns = [
    path('page/', notifications.views.get_notifications_page, name='get_notifications_page'),
    path('', notifications.views.list_notifications, name='list_notifications'),
]
