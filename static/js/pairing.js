let keepaliveIntervalID;
let keepaliveAckTimeoutID;
const keepaliveInterval = 10000;
const keepaliveAckTimeout = 10000;
let timeIntervalIDList = [];
const MAX_KEEPALIVE_RETRIES = 5;
let keepaliveRetries = 0;

$(document).ready(() => {
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
    websocketManager.add_handler("pairing", "keepalive_ack", keepaliveAckHandler);
});

function setIntervalAndExecute(callback, interval) {
    callback();
    return setInterval(callback, interval);
}

function processNewElapsedTime(elapsedTimeElements) {
    elapsedTimeElements.each(function () {
        // Set the initial seconds elapsed
        $(this).data("seconds-elapsed", $(this).data("seconds-elapsed") ?? 0);

        const timeIntervalID = setIntervalAndExecute(() => {
            elapsedTimeElements.each(function () {
                let secondsElapsed = parseInt($(this).data("seconds-elapsed"));
                $(this).data("seconds-elapsed", secondsElapsed + 1);
                $(this).text(formatSeconds(secondsElapsed));
            });
        }, 1000);
        timeIntervalIDList.push(timeIntervalID);
    });
}

function formatSeconds(seconds) {
    let minutes = Math.floor(seconds / 60);
    let remainingSeconds = seconds % 60;
    let minutesString = minutes < 10 ? `0${minutes}` : minutes;
    let secondsString = remainingSeconds < 10 ? `0${remainingSeconds}` : remainingSeconds;

    return `${minutesString}:${secondsString}`;
}

function startKeepaliveLoop() {
    keepaliveIntervalID = setIntervalAndExecute(function () {
        last_date = Date.now();
        websocketManager.pairing_keepalive();
        resetKeepaliveAckTimeout();
    }, keepaliveInterval);
}

function stopKeepaliveLoop() {
    clearInterval(keepaliveIntervalID);
    clearTimeout(keepaliveAckTimeoutID); // Clear the timeout as well, as we wont expect any more acks
}

function setBannerServerError() {
    const pairingBanner = $("#pairing-banner");
    pairingBanner.removeClass("connection-error").addClass("server-error");
}

function setNoAckError() {
    const pairingBanner = $("#pairing-banner");
    pairingBanner.removeClass("server-error").addClass("connection-error");
}

function removeBannerError() {
    const pairingBanner = $("#pairing-banner");
    pairingBanner.removeClass("server-error connection-error");
}

function increaseKeepaliveRetries() {
    keepaliveRetries++;
    if (keepaliveRetries >= MAX_KEEPALIVE_RETRIES) {
        console.error("Max keepalive retries reached. Cancelling pairing.");
        stopKeepaliveLoop();
    }
}

function resetKeepaliveAckTimeout() {
    clearTimeout(keepaliveAckTimeoutID);
    keepaliveAckTimeoutID = setTimeout(() => {
        setNoAckError();
        increaseKeepaliveRetries();
    }, keepaliveAckTimeout);
}

function keepaliveAckHandler(data) {
    clearTimeout(keepaliveAckTimeoutID);
    if (data["status"] === "success") {
        removeBannerError();
        keepaliveRetries = 0;
    }else if (data["status"] === "error") {
        setBannerServerError();
        increaseKeepaliveRetries();
    }else {
        console.error("Invalid status in keepalive_ack:", data["status"]);
    }
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
    pairingBanner.remove();

    // Stop the keepalive loop
    stopKeepaliveLoop();

    // Stop all elapsed time intervals
    timeIntervalIDList.forEach((id) => clearInterval(id));
}

function cancelPairing(buttonElement) {
    const pairingBanner = $("#pairing-banner");
    const isError = pairingBanner.hasClass("connection-error") || pairingBanner.hasClass("server-error");
    if (isError) {
        cancelPairingHandler({});
    } else {
        $(buttonElement).outerHTML = `<span class="spinner-border" role="status" aria-hidden="true"></span>`;
    }

    // send the cancel pairing request to the server (we can still try to cancel if there is an error)
    websocketManager.cancel_pairing();
}

function requestPairing(desiredStance, debateId) {
    websocketManager.request_pairing(desiredStance, debateId);
}
