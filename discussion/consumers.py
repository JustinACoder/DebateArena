from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q

from discussion.forms import MessageForm
from discussion.models import Discussion


class MessageConsumer(AsyncJsonWebsocketConsumer):
    """
    This consumer handles messages sent in discussions.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.discussion_ids = None

    @database_sync_to_async
    def get_discussion_ids(self):
        # list to force evaluation of the queryset
        return set(Discussion.objects.filter(
            Q(participant1=self.scope['user']) | Q(participant2=self.scope['user'])
        ).values_list('id', flat=True))

    @database_sync_to_async
    def save_message_to_db(self, content, discussion_id):
        messageForm = MessageForm({'text': content['message']})

        if messageForm.is_valid():
            message = messageForm.save(commit=False)
            message.discussion_id = discussion_id
            message.author = self.scope['user']
            message.save()
            return True
        else:
            return False

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(reason='You are not authenticated')
            return

        await self.accept()

        # join all groups for which the user is a participant
        self.discussion_ids = await self.get_discussion_ids()
        for discussion_id in self.discussion_ids:
            await self.channel_layer.group_add(
                str(discussion_id),
                self.channel_name
            )

    async def disconnect(self, close_code):
        # remove from all groups
        for discussion_id in self.discussion_ids:
            await self.channel_layer.group_discard(
                str(discussion_id),
                self.channel_name
            )
        await self.close()

    async def receive_json(self, content, **kwargs):
        # check that we have an integer discussion_id and a non-empty message
        discussion_id = content.get('discussion_id', None)
        message = str(content.get('message', ''))
        if not isinstance(discussion_id, int) or not message.strip():
            await self.send_json({'error': 'Invalid message'})
            return

        # check that the user is a participant in the discussion
        if discussion_id not in self.discussion_ids:
            await self.send_json({'error': 'You are not a participant in this discussion'})
            return

        # save the message to the database
        valid_message = await self.save_message_to_db(content, discussion_id)

        # send the message to the group
        if valid_message:
            await self.channel_layer.group_send(
                str(discussion_id),
                {
                    'type':  'message',
                    'discussion_id': discussion_id,
                    'sender_id': self.scope['user'].id,
                    'sender': self.scope['user'].username,
                    'message': message,
                }
            )
        else:
            await self.send_json({'error': 'Invalid message'})

    async def message(self, event):
        await self.send_json(event)
