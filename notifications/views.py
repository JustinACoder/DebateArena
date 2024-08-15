from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseBadRequest
from django.shortcuts import render


@login_required
def get_notifications_page(request):
    notifications = request.user.notification_set.all().order_by('-created_at')
    is_dropdown = request.GET.get('dropdown', False)

    # Paginate the notifications
    paginator = Paginator(notifications, 10)
    try:
        page = paginator.page(request.GET.get('page', '1'))
    except EmptyPage:
        return HttpResponseBadRequest('Invalid page number')

    context = {
        'page': page,
        'is_dropdown': is_dropdown
    }

    return render(request, 'notifications/notifications_list_page.html', context)

@login_required
def list_notifications(request):
    return render(request, 'notifications/notifications_list.html')
