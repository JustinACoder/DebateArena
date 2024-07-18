/* jQuery custom plugin for toast notifications on DebateArena */
/* this plugin requires bootstrap 5 css for styling */
(function ($) {
    const typeToConfig = {
        'success': {'bg': 'bg-success', 'icon': 'bi-check-circle-fill'},
        'error': {'bg': 'bg-danger', 'icon': 'bi-x-circle-fill'},
        'warning': {'bg': 'bg-warning', 'icon': 'bi-exclamation-circle-fill'},
        'info': {'bg': 'bg-info', 'icon': 'bi-info-circle-fill'},
        'debug': {'bg': 'bg-secondary', 'icon': 'bi-bug-fill'}
    };

    $.extend({
        toast: function (type, message, autohide = true, delay = 5000) {
            if (!typeToConfig.hasOwnProperty(type)) {
                console.error('Invalid toast type: ' + type);
                return;
            } else if (typeof message !== 'string') {
                console.error('Invalid toast message: ' + message);
                return;
            }else if (typeof delay !== 'number' || delay < 0) {
                console.error('Invalid toast delay: ' + delay);
                return;
            }

            let toastTemplate = `
                <div class="toast rounded-pill align-items-center text-white ${typeToConfig[type].bg}" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex align-items-center">
                        <div class="toast-body col d-flex align-items-center py-1 ps-3">
                            <i class="bi ${typeToConfig[type].icon} me-2 fs-1"></i>
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white col-auto pe-3 me-2" style="height: 2em" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            `;
            const $toast = $(toastTemplate);

            // Append the toast to the body
            $('#toastPlacement').prepend($toast);

            // Initialize the toast
            let toastElement = new bootstrap.Toast($toast.get(0), {'autohide': autohide, 'delay': delay});

            // Show the toast
            toastElement.show();

            return $toast;
        }
    });
}(jQuery));