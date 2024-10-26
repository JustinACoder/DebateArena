class WebSocketManager {
    constructor() {
        this.socket = null;
        this.handlers = {};
        this.messageQueue = [];  // Queue to hold messages until connection is ready
        this.isConnected = false;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this.socket = new WebSocket(`${protocol}://${window.location.host}/ws/`);

        // Flush queued messages once the connection is established
        this.socket.onopen = () => {
            this.isConnected = true;
            while (this.messageQueue.length > 0) {
                this.socket.send(this.messageQueue.shift());
            }
        };

        this.socket.onmessage = this.on_message.bind(this);

        // Handle connection close or error by resetting the connection state
        this.socket.onclose = () => {
            this.isConnected = false;
            // TODO: reconnection logic?
            $.toast('error', 'Websocket connection closed. Please refresh the page', false);
        };

        this.socket.onerror = () => {
            this.isConnected = false;
            // TODO: reconnection logic?
            $.toast('error', 'Error connecting to the websocket server', false);
        };
    }

    add_handler(stream, event_type, handler) {
        let handler_key = stream + '.' + event_type;
        this.handlers[handler_key] = handler;
    }

    on_message(event) {
        let wsMessage = JSON.parse(event.data);
        let payload = wsMessage['payload'];

        if (payload['status'] === 'error') {
            $.toast('error', `Error websocket status (${payload['event_type']}): ${payload['message']}`, false);
            return;
        }

        let handler_key = wsMessage['stream'] + '.' + payload['event_type'];
        if (handler_key in this.handlers) {
            let handler = this.handlers[handler_key];
            handler(payload['data']);
        } else {
            console.log(`No handler for ${handler_key}, the available handlers are: ${Object.keys(this.handlers)}`);
        }
    }

    // Generic send method that queues if the socket is not ready
    send(data) {
        const message = JSON.stringify(data);
        if (this.isConnected) {
            this.socket.send(message);
        } else {
            this.messageQueue.push(message);
        }
    }

    send_chat_message(discussionId, message) {
        this.send({
            'stream': 'discussion',
            'payload': {
                'event_type': 'new_message',
                'data': {
                    'message': message,
                    'discussion_id': discussionId
                }
            }
        });
    }

    set_notification_read(notificationId, is_read) {
        this.send({
            'stream': 'notification',
            'payload': {
                'event_type': 'set_read',
                'data': {
                    'notification_id': notificationId,
                    'is_read': is_read
                }
            }
        });
    }

    read_messages(currentDiscussionId) {
        this.send({
            'stream': 'discussion',
            'payload': {
                'event_type': 'read_messages',
                'data': {
                    'discussion_id': currentDiscussionId
                }
            }
        });
    }
}

// Usage
const websocketManager = new WebSocketManager();
websocketManager.connect();
