from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST


@login_required
def get_notifications_page(request):
    notifications = request.user.notification_set.all().order_by('-created_at')

    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
    is_dropdown = request.GET.get('dropdown', 'false').lower() == 'true'
    if unread_only:
        notifications = notifications.filter(read=False)

    # Paginate the notifications
    paginator = Paginator(notifications, 10)
    try:
        page = paginator.page(request.GET.get('page', '1'))
    except EmptyPage:
        return HttpResponseBadRequest('Invalid page number')

    context = {
        'page': page,
        'is_dropdown': is_dropdown,
        'unread_only': unread_only
    }

    return render(request, 'notifications/notifications_list_page.html', context)


@login_required
def list_notifications(request):
    return render(request, 'notifications/notifications_list_full.html')


@login_required
@require_POST
def delete_notification(request, notification_id):
    #request.user.notification_set.filter(id=notification_id).delete()
    return HttpResponse(status=204)
