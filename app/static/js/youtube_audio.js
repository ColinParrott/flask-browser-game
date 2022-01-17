const jaydenSongDuration = 13000;

// 2. This code loads the IFrame Player API code asynchronously.
var tag = document.createElement('script');

tag.src = "https://www.youtube.com/iframe_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

// 3. This function creates an <iframe> (and YouTube player)
//    after the API code downloads.
var player;
var timeout;
var ready_timeout;
var playerReady = false;
var alreadyStopped = false;

function onYouTubeIframeAPIReady() {
    player = new YT.Player('player', {
        height: '0',
        width: '0',
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

function onPlayerReady(event) {
    event.target.setVolume(10);
    playerReady = true;
}

function onPlayerStateChange(event) {
    if (event.data == YT.PlayerState.PLAYING && !alreadyStopped)
    {   alreadyStopped = true;
        timeout = setTimeout(finalStopVideo, jaydenSongDuration);
    }
}

function playYouTubeAudio(id, startTime) {
    alreadyStopped = false;
    if (playerReady) {
        clearTimeout(ready_timeout);
        clearTimeout(timeout);
        stopVideo();
        player.loadVideoById(
            {
                'videoId': id,
                'startSeconds': startTime,
                'suggestedQuality': 'small'
            }
        );
    }
    else {
        if (ready_timeout != null)
            clearTimeout(ready_timeout)

        ready_timeout = setTimeout(function () {
            innerLoad(id, startTime)
        }, 500);
    }

}

function innerLoad(id, startTime)
{
        if (playerReady) {
        clearTimeout(ready_timeout);
        clearTimeout(timeout);
        stopVideo();
        player.loadVideoById(
            {
                'videoId': id,
                'startSeconds': startTime,
                'suggestedQuality': 'small'
            }
        );
    }
    else {
        if (ready_timeout != null)
            clearTimeout(ready_timeout)

        ready_timeout = setTimeout(function () {
            innerLoad(id, startTime)
        }, 500);
    }
}

function finalStopVideo() {
    player.stopVideo();
    toggle_spotify(true);
}

function stopVideo() {
    player.stopVideo();
}