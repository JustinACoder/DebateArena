from channels.db import database_sync_to_async
from django.db.models import Q

from ProjectOpenDebate.consumers import CustomBaseConsumer, get_user_group_name
from .models import Notification


class NotificationConsumer(CustomBaseConsumer):
    """
    This consumer handles the WebSocket connection for sending and reading Notifications.
    """

    @database_sync_to_async
    def get_notification(self, notification_id, user):
        """
        Get the notification from the database.

        :param notification_id: The ID of the notification
        :param user: The user who is trying to get the notification
        :return: The notification object
        """
        return Notification.objects.get(id=notification_id, user=user)

    async def receive_json(self, content, **kwargs):
        """
        Receives a JSON message from the client and processes it.
        Note: all the data here is untrusted, so we should validate it before processing it.

        :param content: The JSON message from the client
        :param kwargs: Additional arguments
        """
        # Get the data from the content
        data = content.get('data', {})

        # check that we have an integer notification_id and an event_type
        notification_id = data.get('notification_id')
        event_type = str(content.get('event_type', ''))
        if not isinstance(notification_id, int) or not event_type:
            await self.send_json({'status': 'error', 'message': 'Missing notification_id or event_type'})
            return

        # Get the user from the scope
        user = self.scope['user']

        # check that the notification exists and belongs to the user
        try:
            notification = await self.get_notification(notification_id, user)
        except Notification.DoesNotExist:
            await self.send_json({'status': 'error', 'message': 'You are not a participant in this discussion'})
            return

        # Process the event according to the event_type
        if event_type == 'read':
            await self.process_read_event(notification)
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid event_type'})

    async def process_read_event(self, notification):
        # Mark the notification as read
        notification.read = True
        notification.save()

        # Send message to the user group to update the notification list
        user_group_name = get_user_group_name(self.__class__.__name__, notification.user.id)
        await self.channel_layer.group_send(
            user_group_name,
            {
                'status': 'success',
                'event_type': 'read',
                'type': 'send.json',
                'data': {
                    'notification_id': notification.id,
                }
            }
        )
