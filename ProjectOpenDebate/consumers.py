from channels.generic.websocket import AsyncJsonWebsocketConsumer


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
