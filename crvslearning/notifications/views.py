from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

@login_required
def notification_list(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications
    })

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect(notification.url or 'home')