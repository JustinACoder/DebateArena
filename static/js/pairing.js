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

function cancelPairing() {
  alert("Pairing cancelled");
}
