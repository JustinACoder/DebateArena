from channels.generic.websocket import AsyncJsonWebsocketConsumer


def get_user_group_name(user_id):
    return f"user_{user_id}"


class UserConsumer(AsyncJsonWebsocketConsumer):
    """
    This consumer handles all messages directed to a user. It then delegates the message to the appropriate handler.
    Each app should have a handlers.py file that contains the handlers for that app. To associate a message with a
    handler, we check the type of the message and then call the appropriate handler. The handlers are passed to the
    consumer when it is instantiated. We can import the handlers from the handlers.py file of the app directly into
    the consumer constructor. For instance, it could look like this:
    import myapp1.handlers.config as myapp1_handlers_config
    import myapp2.handlers.config as myapp2_handlers_config

    URLRouter([
        path("ws/", UserConsumer.as_asgi(
            myapp1=myapp1_handlers_config,
            myapp2=myapp2_handlers_config,
        )),
    ])

    The type should have the format <app>.<handler>

    The format of the json message should be:
    {
        "type": "<app>.<handler>",
        "data": {
            ...
        }
    }

    Handlers should have the following signature:
    async def handler(consumer, data):
        pass
    """

    def __init__(self, **handler_configs):
        super().__init__()
        self.handlers = {}
        for app, handler_config in handler_configs.items():
            for handler_name, handler in handler_config.items():
                self.handlers[f"{app}.{handler_name}"] = handler

    async def connect(self):
        # Only accept authenticated users
        # TODO: Maybe we should allow unauthenticated users to connect to the websocket and allow the handlers to
        #  decide what to do with them
        if not self.scope['user'].is_authenticated:
            await self.close(reason='You are not authenticated')
            return

        await self.accept()

        # Connect to the user group
        await self.channel_layer.group_add(
            get_user_group_name(self.scope['user'].id),
            self.channel_name
        )

    async def receive_json(self, content, **kwargs):
        """
        This method is called when a message is received. It delegates the message to the appropriate handler.

        :param content: The content of the message
        :param kwargs: Additional keyword arguments
        """
        handler = self.handlers.get(content['event_type'])
        data = content.get('data')

        # If the handler is not found, send an error message
        if not handler:
            await self.send_json({
                'status': 'error',
                'event_type': 'main',
                'message': 'Unknown handler'
            })

        # If there are no data, send an error message
        if not data:
            await self.send_json({
                'status': 'error',
                'event_type': 'main',
                'message': 'No data provided'
            })

        # Call the handler
        await handler(self, data)

    async def disconnect(self, close_code):
        await self.close()
