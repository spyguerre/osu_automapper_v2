from pynput.keyboard import Key, KeyCode, Listener
import json
from dataclasses import dataclass
from typing import List, Literal, Set, Optional, Dict, Tuple
import os
import vlc
import time
import threading


START_OFFSET:   int                = 100
FST_PSE_OFFSET: int                = -120

REC_KEYS:       Set[Key | KeyCode] = {KeyCode.from_char("e"), KeyCode.from_char("r")}
BACK_KEY:       Key | KeyCode      = Key.left
FWD_KEY:        Key | KeyCode      = Key.right
SLOWER_KEY:     Key | KeyCode      = Key.down
FASTER_KEY:     Key | KeyCode      = Key.up
PLAY_KEY:       Key | KeyCode      = Key.space
PAUSE_KEY:      Key | KeyCode      = Key.space
QUIT_KEY:       Key | KeyCode      = Key.esc
  
IN_SONG_DIR:    str                = "record_taps"
OUT_PATH:       str                = os.path.join(IN_SONG_DIR, "recording.json")


class VLCClock():
    def __init__(self) -> None:
        # When playing media, self.pc_t0 represents the time at which the media would have started playing
        # without interruption to be at the current state right now.
        # Contains None whenever the media is paused.
        # 
        # Examples:
        # 
        # - Audio started playing at t0, it is now t1:
        # self.pc_t0 == t0, since t1 - t0 is the time it took to get there without interruption
        # 
        # - Audio started playing at t0, user skipped 1 second forward at t1, and it is now t2:
        # self.pc_t0 == t0 - 1000, since it would have taken 1000 more ms to play the media from start to current media time, than the amount of time elapsed since the user actually started playing media
        #
        # - Audio started playing at t0, and user set playing rate to 1.5 at t1 (it is now still t1):
        # self.pc_t0 == t1 - (t1-t0)/1.5, since it would have taken (t1-t0)/1.5 to reach this point in the media with this rate since the start (instead of (t1-t0)/1.0 for normal playing rate).
        self.pc_t0: Optional[int] = None

        # Number of times self.sync() was called since last self.seek(); used to average pc_t0 over all synced times.
        self.syncs_since_last_seek: int = 0

        # Holds the current media time, in ms, whenever the player is paused, otherwise contains None.
        self.paused_media_time: Optional[int] = 1

        # Boolean indicating whether further user inputs have to be blocked right now
        # (typically used when waiting for player initialization after seeks)
        self.lock: bool = False

        # Determines which offset to use, depending on whether the last seek time was in the first media buffer window
        self.non_trivial_seek: bool = False

        self.config_player()

    def get_song_path(self) -> Optional[str]:
        for file in os.listdir(IN_SONG_DIR):
            if file.endswith(".mp3"):
                return os.path.join(IN_SONG_DIR, file)

    def config_player(self, volume: int = 42, rate: float = 1.) -> None:
        # Load media
        media = instance.media_new(self.get_song_path())
        player.set_media(media)

        # Ensure correct load of media
        assert player.get_media() is not None
        assert player.get_media().get_mrl() is not None

        # Custom player params
        player.audio_set_volume(volume)
        player.set_rate(rate)

    def seek(self, seek_time: int) -> None:
        self.lock = True

        self.non_trivial_seek = seek_time >= 500

        timeout = time.perf_counter() + 5.  # In seconds here
        player.play()
        # Wait until the player actually plays audio, waiting only for playing state is not enough
        while time.perf_counter() < timeout:
            if player.get_time() > 0 and player.is_playing():
                self.syncs_since_last_seek = 0
                player.set_time(seek_time)  # Reset the player to the desired time
                self.sync()  # The thread will call sync soon. Also call it here to make sure we're fast enough
                self.lock = False
                return
            time.sleep(0.001)

        self.lock = False
        raise RuntimeError("VLC failed to start playback after seek.")

    def change_rate(self, new_rate: float) -> None:
        self.pause()  # Work with actual media time instead of computed, which would cause discontinuity between media time before and after rate change
        media_time = self.get_media_time()
        print(media_time)
        player.set_rate(new_rate)
        self.seek(media_time)

    def pause(self) -> None:
        self.paused_media_time = self.get_media_time()
        self.pc_t0 = None
        if player.is_playing():
            player.pause()

    def play(self) -> None:
        self.seek(self.paused_media_time)
        self.paused_media_time = None

    def sync(self) -> None:
        # Since this method is only called whenever the media time was just updated,
        # we can synchronize cur_pc_time to the media_time (which is, right now only, ground truth)
        cur_media_time = player.get_time()
        cur_pc_time = time.perf_counter()*1000
        
        player_rate = player.get_rate()
        
        # Compute pc_t0 as described at its definition
        synced_pc_t0 = int(cur_pc_time - cur_media_time / player_rate)
        # Update the field with the average of synced pc_t0's since last seek
        self.pc_t0 = int((self.syncs_since_last_seek*(self.pc_t0 if self.pc_t0 is not None else 0) + 1*synced_pc_t0) / (self.syncs_since_last_seek + 1))

        self.syncs_since_last_seek += 1

    def get_media_time(self, pc_t1: Optional[int] = None) -> int:
        if pc_t1 is None:
            pc_t1 = int(time.perf_counter()*1000)

        if self.pc_t0 is None:  # In this case, the media is paused; current media time is stored in paused_media_time
            return self.paused_media_time

        return int((pc_t1-self.pc_t0) * player.get_rate())


instance: vlc.Instance    = vlc.Instance("--file-caching=50")
player:   vlc.MediaPlayer = instance.media_player_new()
clock:    VLCClock        = VLCClock()


# Class representing a single keyboard event: pressing or releasing a key
@dataclass()
class PressEvent:
    time:         int                          # Time in ms from start of recording
    dflt_offset:  int                          # Default offset to apply to this event
    key:          Key | KeyCode                # The key pressed or released
    type:         Literal["press", "release"]  # Whether event is a press (True) or a release (False) event

# Class representing a tap event: both press and release of a key
@dataclass()
class TapEvent:
    time:         int            # In ms
    time_end:     int            # In ms
    dflt_offset:  int            # Default measure offset to apply to this tap event
    key:          Key | KeyCode  # The key pressed and released


def player_go_back(time: int = 5000) -> None:
    clock.seek(max(0, clock.get_media_time() - time))

def player_incr_rate(rate: float = 0.1) -> None:
    clock.change_rate(player.get_rate() + rate)

def on_press(key: Key | KeyCode, events: List[PressEvent]) -> Optional[Literal[False]]:
    # First check if user wants to quit
    if key == QUIT_KEY:
        return False  # Exit recording
    
    # If clock is already treating a player action, drop the user event until audio is playing properly again
    if clock.lock:
        return
    
    # Treat user event
    if key in REC_KEYS:
        events.append(PressEvent(
            time        = clock.get_media_time(),
            dflt_offset = -FST_PSE_OFFSET if clock.non_trivial_seek else -START_OFFSET,
            key         = key,
            type        = "press"
        ))

    elif key == BACK_KEY:
        if not player.is_playing():
            return
        
        ms_amount: int = 5000

        # Additionally, remove all press events of type "press" in the event list
        pc_cur_time = int(time.perf_counter()*1000)
        cur_time = clock.get_media_time(pc_cur_time)
        back_time = clock.get_media_time(pc_cur_time - ms_amount)  # Compute with clock.get_time to take into account playing rate
        old_ev_len = len(events)
        events[:] = [event for event in events if not (back_time <= event.time <= cur_time and event.type == "press")]
        new_ev_len = len(events)

        player_go_back(ms_amount)  # Back 5 seconds

        print(f"Jumped back to {print_ms_time(clock.get_media_time())}, removing {old_ev_len - new_ev_len} press events.")


    elif key == FWD_KEY:
        if player.is_playing():
            player_go_back(-5000)  # Forward 5 seconds
            print(f"Jumped forward to {print_ms_time(clock.get_media_time())}")

    elif key == SLOWER_KEY:
        if player.is_playing():
            player_incr_rate(-0.1)  # Slower by 10%
            print(f"Decreased playing rate to {player.get_rate()}")

    elif key == FASTER_KEY:
        if player.is_playing():
            player_incr_rate(0.1)  # Faster by 10%
            print(f"Increased playing rate to {player.get_rate()}")

    elif key == PLAY_KEY and key == PAUSE_KEY:
        # Same key for pause and play, make it toggle mode
        if player.is_playing():
            clock.pause()
            print(f"Paused at {print_ms_time(clock.get_media_time())}.")
        else:
            clock.play()
            print(f"Playing at {print_ms_time(clock.get_media_time())}...")

    elif key == PLAY_KEY:
        # Different keys for pause and play, treat press as absolute "play" order
        clock.play()
        print(f"Playing at {print_ms_time(clock.get_media_time())}...")

    elif key == PAUSE_KEY:
        clock.pause()
        print(f"Paused at {print_ms_time(clock.get_media_time())}.")


def on_release(key: Key | KeyCode, events: List[PressEvent]) -> None:
    if key in REC_KEYS:
        events.append(PressEvent(
            time        = clock.get_media_time() - (FST_PSE_OFFSET if clock.non_trivial_seek else START_OFFSET),
            dflt_offset = -FST_PSE_OFFSET if clock.non_trivial_seek else -START_OFFSET,
            key         = key,
            type        = "release"
        ))


def record() -> List[PressEvent]:
    events: List[PressEvent] = []
    
    with Listener(
            on_press=lambda key : on_press(key, events),
            on_release=lambda key : on_release(key, events)
        ) as listener:
        listener.join()

    return events


def press_to_taps(events: List[PressEvent]) -> List[TapEvent]:
    press_dict: Dict[Key | KeyCode, Tuple[int, int]] = {}
    res: List[TapEvent] = []
    for event in events:
        match event.type:
            case "press":
                if event.key in press_dict.keys():  # Ignore repeated press events that are never released (happens when holding press usually)
                    continue
                press_dict[event.key] = (event.time, event.dflt_offset)

            case "release":
                if event.key not in press_dict.keys():  # Ignore release events that have no corresponding press events (can happen when pressing back)
                    continue
                press_info = press_dict.pop(event.key)
                res.append(TapEvent(
                    time        = press_info[0],
                    time_end    = event.time + event.dflt_offset,  # Add default offset directly, for release only
                    dflt_offset = press_info[1],
                    key         = event.key
                ))
    return res


def serialize_key(key: Key | KeyCode) -> Optional[str]:
    if isinstance(key, KeyCode):
        return key.char
    else:
        return key.name

def serialize_event(event: TapEvent) -> Dict[str, Optional[int | str]]:
    return {
        "time": event.time,
        "time_end": event.time_end,
        "key": serialize_key(event.key),
    }

def serialize_events(events: List[TapEvent]) -> List[Dict[str, Optional[int | str]]]:
    return [serialize_event(event) for event in events]

def print_ms_time(ms: int) -> str:
    minutes = int(ms/(60*1000))
    ms -= minutes*60*1000
    seconds = int(ms/(1000))
    ms -= minutes*1000
    return f"{minutes:02d}:{seconds:02d}.{ms}"


# Watches the player.get_time() updates to synchronize the VLCClock object with media time as frequently as possible.
def monitor_media_time(player: vlc.MediaPlayer, clock: VLCClock) -> None:
    last_media_time: Optional[int] = None

    while True:
        cur_media_time: int = player.get_time()
        if last_media_time != cur_media_time:
            clock.sync()
            last_media_time = cur_media_time

        time.sleep(0.001)


if __name__ == "__main__":
    # Start monitor thread
    threading.Thread(
        target = monitor_media_time,
        args   = (player, clock),
        daemon = True
    ).start()

    events = record()
    taps = press_to_taps(events)

    json.dump(serialize_events(taps), open(OUT_PATH, "w"))
