from public.models import Notification

def notifications_processor(request):
    if request.user.is_authenticated:
        # Fetch 5 latest unread notifications or all latest if needed
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {
            'latest_notifications': notifications,
            'unread_notifications_count': unread_count
        }
    return {
        'latest_notifications': [],
        'unread_notifications_count': 0
    }
