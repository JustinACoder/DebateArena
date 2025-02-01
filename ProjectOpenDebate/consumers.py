from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.shortcuts import resolve_url


def get_user_group_name(consumer_class_name: str, user_id: int):
    return f'{consumer_class_name}_{user_id}'


class CustomBaseConsumer(AsyncJsonWebsocketConsumer):
    """
    This is the base consumer for this project. It forces the user to be authenticated before connecting.
    It also handles the connection and disconnection.
    """

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(reason='You are not authenticated')
            return

        await self.accept()

        # Join group
        await self.channel_layer.group_add(
            get_user_group_name(self.__class__.__name__, self.scope['user'].id),
            self.channel_name
        )

    async def disconnect(self, close_code):
        await self.close(code=close_code)

    async def redirect(self, user_id, to, *args, **kwargs):
        """
        Redirects the user to the specified URL.
        """
        url = resolve_url(to, *args, **kwargs)
        group = get_user_group_name(self.__class__.__name__, user_id)

        await self.channel_layer.group_send(
            group,
            {
                'type': 'send.json',
                'event_type': 'redirect',
                'data': {
                    'url': url
                }
            }
        )
