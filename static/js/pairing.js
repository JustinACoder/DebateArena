let elapsedTimeElementsList = $();

$(document).ready(() => {
    setInterval(() => {
        elapsedTimeElementsList.each(function () {
            let secondsElapsed = parseInt($(this).data("seconds-elapsed"));
            $(this).data("seconds-elapsed", secondsElapsed + 1);
            $(this).text(formatSeconds(secondsElapsed));
        });
    }, 1000);

    processNewElapsedTime($(".elapsed-time"));

    // Bind websocket handlers
    websocketManager.add_handler("pairing", "request_pairing", requestPairingHandler);
    websocketManager.add_handler("pairing", "start_search", startSearchHandler);
    websocketManager.add_handler("pairing", "match_found", matchFoundHandler);
    websocketManager.add_handler("pairing", "cancel", cancelPairingHandler);
});

function processNewElapsedTime(elapsedTimeElements) {
    elapsedTimeElements.each(function () {
        // Set the initial seconds elapsed
        $(this).data("seconds-elapsed", $(this).data("seconds-elapsed") ?? 0);
    })

    // Add the new element to the list
    elapsedTimeElementsList = elapsedTimeElementsList.add(elapsedTimeElements);
}

function formatSeconds(seconds) {
    let minutes = Math.floor(seconds / 60);
    let remainingSeconds = seconds % 60;
    let minutesString = minutes < 10 ? `0${minutes}` : minutes;
    let secondsString = remainingSeconds < 10 ? `0${remainingSeconds}` : remainingSeconds;

    return `${minutesString}:${secondsString}`;
}


function requestPairingHandler(data) {
    const container = $("#pairing-banner-container");
    container.html(data["html"]);
    processNewElapsedTime(container.find(".elapsed-time"));
}

function startSearchHandler(data) {
    console.log("Start search!");
}

function matchFoundHandler(data) {
    const pairingBanner = $("#pairing-banner");
    pairingBanner.addClass("match-found");
}

function cancelPairingHandler(data) {
    const pairingBanner = $("#pairing-banner");
    const isFromCurrentUser = data["from_current_user"];

    if (isFromCurrentUser) {
        pairingBanner.remove();
    } else {
        pairingBanner.removeClass("match-found");
    }
}

function cancelPairing(buttonElement) {
    $(buttonElement).outerHTML = `<span class="spinner-border" role="status" aria-hidden="true"></span>`;

    // send the cancel pairing request
    websocketManager.cancel_pairing();
}

function requestPairing() {
    websocketManager.request_pairing();
}





