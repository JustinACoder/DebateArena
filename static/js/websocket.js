const WS_CONNECT_MAX_RETRIES = 5;

class WebSocketManager {
    constructor() {
        this.socket = null;
        this.handlers = {};
        this.messageQueue = [];  // Queue to hold messages until connection is ready
        this.isConnected = false;

        if (!("WebSocket" in window)) {
            $.toast('error', 'Your browser does not support WebSockets. Please upgrade to a modern browser.', false);
        }
    }

    connect(num_retries = WS_CONNECT_MAX_RETRIES) {
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
        this.socket.onclose = (event) => {
            this.isConnected = false;
            console.warn('Websocket connection closed:', event);
            this.reconnect(num_retries);
        };

        this.socket.onerror = (event) => {
            this.isConnected = false;
            console.error('Websocket connection error:', event);
            this.reconnect(num_retries);
        };

        // Bind this instance to this object for all methods
        // Source: https://stackoverflow.com/a/72197516/14107875
        Object.getOwnPropertyNames(WebSocketManager.prototype).forEach((key) => {
            if (key !== 'constructor') {
                this[key] = this[key].bind(this);
            }
        });
    }

    reconnect(num_retries) {
        if (num_retries > 0) {
            $.toast('warning', 'Disconnected. Reconnecting...', true, 2000);
            setTimeout(() => {
                this.connect(num_retries - 1);
            }, 3000);
        } else {
            $.toast('error', 'Could not connect to the websocket server. Please refresh the page and contact support if the issue persists.', false);
        }
    }

    add_handler(stream, event_type, handler) {
        let handler_key = stream + '.' + event_type;
        let handlers_for_key = this.handlers[handler_key];
        if (handlers_for_key) {
            handlers_for_key.push(handler);
        } else {
            this.handlers[handler_key] = [handler];
        }
    }

    on_message(event) {
        let wsMessage = JSON.parse(event.data);
        let payload = wsMessage['payload'];

        if (payload['event_type'] === 'redirect') {
            window.location.href = payload['data']['url'];
        }

        if ((payload['message'] || payload['status'] === 'error') && payload['no_toast'] !== true) {
            const message = payload['message'] ?? 'An unknown error occurred';
            const shouldAutohide = payload['status'] === 'success';
            $.toast(payload['status'] ?? 'info', message, shouldAutohide);
        }

        let handler_key = wsMessage['stream'] + '.' + payload['event_type'];
        if (handler_key in this.handlers) {
            let handlers_for_key = this.handlers[handler_key];
            for (let handler of handlers_for_key) {
                let data = payload['data'] ?? {};
                data['status'] = data['status'] ?? payload['status'];
                handler(data);
            }
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

    read_messages(currentDiscussionId, through_load_discussion = false) {
        this.send({
            'stream': 'discussion',
            'payload': {
                'event_type': 'read_messages',
                'data': {
                    'discussion_id': currentDiscussionId,
                    'through_load_discussion': through_load_discussion
                }
            }
        });
    }

    request_pairing(desiredStance, debateId) {
        this.send({
            'stream': 'pairing',
            'payload': {
                'event_type': 'request_pairing',
                'data': {
                    'desired_stance': desiredStance,
                    'debate_id': debateId
                }
            }
        });
    }

    cancel_pairing() {
        this.send({
            'stream': 'pairing',
            'payload': {
                'event_type': 'cancel',
                'data': {}
            }
        });
    }

    start_search() {
        this.send({
            'stream': 'pairing',
            'payload': {
                'event_type': 'start_search',
                'data': {}
            }
        });
    }

    pairing_keepalive() {
        this.send({
            'stream': 'pairing',
            'payload': {
                'event_type': 'keepalive',
                'data': {}
            }
        });
    }
}

// Usage
const websocketManager = new WebSocketManager();
websocketManager.connect();
