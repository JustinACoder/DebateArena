let elapsedTimeElementsList = $();
let keepaliveIntervalID;
let timeIntervalID;

$(document).ready(() => {
    timeIntervalID = setInterval(() => {
        elapsedTimeElementsList.each(function () {
            let secondsElapsed = parseInt($(this).data("seconds-elapsed"));
            $(this).data("seconds-elapsed", secondsElapsed + 1);
            $(this).text(formatSeconds(secondsElapsed));
        });
    }, 1000);

    // if the pairing banner is present, start the keepalive loop and process the new elapsed time elements
    const pairingBanner = $("#pairing-banner");
    if (pairingBanner.length) {
        processNewElapsedTime(pairingBanner.find(".elapsed-time"));
        startKeepaliveLoop();
    }

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

function startKeepaliveLoop() {
    keepaliveIntervalID = setInterval(websocketManager.pairing_keepalive, 10000); // TODO: To constant?
}

function requestPairingHandler(data) {
    const container = $("#pairing-banner-container");
    container.html(data["html"]);
    processNewElapsedTime(container.find(".elapsed-time"));
    startKeepaliveLoop();

    // Indicate to the server that we are ready to start searching
    websocketManager.start_search();
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

    clearInterval(keepaliveIntervalID);
    clearInterval(timeIntervalID);
}

function cancelPairing(buttonElement) {
    $(buttonElement).outerHTML = `<span class="spinner-border" role="status" aria-hidden="true"></span>`;

    // send the cancel pairing request
    websocketManager.cancel_pairing();
}

function requestPairing(desiredStance, debateId) {
    websocketManager.request_pairing(desiredStance, debateId);
}
