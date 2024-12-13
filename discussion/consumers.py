from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.db.models import Q
from django.template.loader import render_to_string

from ProjectOpenDebate.consumers import CustomBaseConsumer, get_user_group_name
from .forms import MessageForm
from .models import Discussion, Message
from .views import set_message_additional_fields


class DiscussionConsumer(CustomBaseConsumer):
    """
    This consumer handles the WebSocket connection for all operations related to discussions.
    """

    async def receive_json(self, content, **kwargs):
        """
        Receives a JSON message from the client and processes it.
        Note: all the data here is untrusted, so we should validate it before processing it.

        :param content: The JSON message from the client
        :param kwargs: Additional arguments
        """
        # Get the data from the content
        data = content.get('data', {})

        # check that we have an integer discussion_id and an event_type
        discussion_id = data.get('discussion_id')
        event_type = str(content.get('event_type', ''))
        if not isinstance(discussion_id, int) or not event_type:
            await self.send_json({'status': 'error', 'message': 'Missing discussion_id or event_type'})
            return

        # Get the user from the scope
        user = self.scope['user']

        # check that the user is a participant in the discussion
        try:
            discussion = await Discussion.objects.aget(Q(participant1=user) | Q(participant2=user), id=discussion_id)
        except Discussion.DoesNotExist:
            await self.send_json({'status': 'error', 'message': 'You are not a participant in this discussion'})
            return

        # Process the event according to the event_type
        if event_type == 'new_message':
            await self.process_new_message(user, discussion, data)
        elif event_type == 'read_messages':
            await self.process_read_messages(user, discussion, data)
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid event_type'})

    async def process_new_message(self, user, discussion, data):
        # Check that the message exists
        message = data.get('message', '').strip()
        if not message:
            await self.send_json({'status': 'error', 'message': 'Missing message'})
            return

        # Save the message to the database
        messageForm = MessageForm({'text': message})
        if messageForm.is_valid():
            messageForm.instance.discussion_id = discussion.id
            messageForm.instance.author = user
            message_instance = await database_sync_to_async(messageForm.save)()
        else:
            await self.send_json({'status': 'error', 'message': 'Invalid message'})
            return

        # mark this message's discussion's read checkpoint as read until this message
        user_readcheckpoint = await discussion.readcheckpoint_set.aget(user=user)
        await database_sync_to_async(user_readcheckpoint.read_until)(message_instance)

        # Set additional fields for the message
        # TODO: This is a bit hacky, we should find a better way to do this
        previous_message = await discussion.message_set.order_by('-created_at').exclude(id=message_instance.id).afirst()
        message_instance.prev_message_created_at = previous_message.created_at if previous_message else None
        set_message_additional_fields(message_instance)

        # If the message is the first message in the group, render the time separator as well
        if message_instance.first_of_group:
            separator_html = render_to_string('discussion/datetime_separator.html',
                                              context={'formatted_datetime': message_instance.formatted_datetime})
        else:
            separator_html = ""

        # Render the message to send to the participants
        context_sender = {
            'message': message_instance,
            'is_current_user': True,
        }
        context_receiver = {
            'message': message_instance,
            'is_current_user': False,
        }
        message_sender_html = render_to_string('discussion/message.html', context=context_sender)
        message_receiver_html = render_to_string('discussion/message.html', context=context_receiver)

        # Send the message to all participants in the discussion
        participants_ids = [discussion.participant1_id, discussion.participant2_id]
        for participant_id in participants_ids:
            user_group_name = get_user_group_name(self.__class__.__name__, participant_id)
            await self.channel_layer.group_send(
                user_group_name,
                {
                    'status': 'success',
                    'event_type': 'new_message',
                    'type': 'send.json',
                    'data': {
                        'discussion_id': discussion.id,
                        'is_archived': discussion.is_archived,
                        'sender_id': user.id,
                        'sender': user.username,
                        'message': message,
                        'html': message_sender_html if participant_id == user.id else message_receiver_html,
                        'separator_html': separator_html,
                        'is_current_user_sender': participant_id == user.id,
                    }
                }
            )

    async def process_read_messages(self, user, discussion, data):
        # TODO: there could be a bug where the user reads the messages, but the other user sends a message before the
        #  read checkpoint is updated. This would mark the message as read even though the user hasn't read it.

        # Get the ReadCheckpoint for the user
        read_checkpoint = await discussion.readcheckpoint_set.aget(user=user)

        # Update the ReadCheckpoint with the current time and latest message
        num_messages_read = await database_sync_to_async(read_checkpoint.read_messages)()

        # If no new messages were read, no need to send the updated ReadCheckpoint information
        if num_messages_read == 0:
            return

        # Send the updated ReadCheckpoint information to BOTH participants
        participants_ids = [discussion.participant1_id, discussion.participant2_id]
        for participant_id in participants_ids:
            user_group_name = get_user_group_name(self.__class__.__name__, participant_id)
            is_current_user = participant_id == user.id
            await self.channel_layer.group_send(
                user_group_name,
                {
                    'status': 'success',
                    'event_type': 'read_messages',
                    'type': 'send.json',
                    'data': {
                        'discussion_id': discussion.id,
                        'is_archived': discussion.is_archived,
                        'is_current_user': is_current_user,
                        'num_messages_read': num_messages_read,  # used to update the unread messages count in navbar
                        'through_load_discussion': data['through_load_discussion']
                    }
                }
            )


