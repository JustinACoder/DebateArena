class WebSocketManager {
    constructor() {
        this.socket = null;
        this.handlers = {};
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this.socket = new WebSocket(`${protocol}://${window.location.host}/ws/`);
        this.socket.onmessage = this.on_message;
    }

    add_handler(stream, event_type, handler) {
        let handler_key = stream + '.' + event_type;
        this.handlers[handler_key] = handler;
    }

    on_message(event) {
        let wsMessage = JSON.parse(event.data);

        let payload = wsMessage['payload'];

        // Check if there was an error
        if (payload['status'] === 'error') {
            $.toast('error', `Error websocket status (${payload['event_type']}): ${payload['message']}`);
            return;
        }

        // Give the message to the appropriate handler
        let handler_key = wsMessage['stream'] + '.' + payload['event_type'];
        let handler = this.handlers[handler_key];
        if (handler !== undefined) {
            handler(payload['data']);
        }else {
            console.log(`No handler for ${handler_key}`);
        }
    }
}

websocketManager = new WebSocketManager();
websocketManager.connect();