from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from ProjectOpenDebate.consumers import get_user_group_name


class Notification(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # GenericForeignKey to link the notification to any object
    # This is useful if we want to link the notification to a specific object for which we can call
    # get_absolute_url() to redirect the user to the object's page.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.TextField()
    related_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f'Notification for {self.user.username} at {self.created_at}'


@receiver(post_save, sender=Notification)
def send_notification(sender, instance, created, **kwargs):
    """
    Send the notification (or updates) to the user using the WebSocket.
    """
    # Get current channel layer
    channel_layer = get_channel_layer()

    # Get the user group name
    user_group_name = get_user_group_name('NotificationConsumer', instance.user.id)

    # Send the notification to the user
    async_to_sync(channel_layer.group_send)(
        user_group_name,
        {
            'status': 'success',
            'event_type': 'new_notification' if created else 'update_notification',
            'type': 'send.json',
            'data': {
                'notification_id': instance.id,
                'message': instance.message,
                'read': instance.read,
                'created_at': instance.created_at.isoformat(),
                'redirect_url': instance.related_object.get_absolute_url() if instance.related_object else ''
            }
        }
    )

