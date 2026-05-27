from pynput.keyboard import Key, KeyCode, Listener
import json
from dataclasses import dataclass
from typing import List, Literal, Set, Optional, Dict, Tuple
import os
import vlc
import time
import threading


FLAT_OFFSET:    int                = 80  # Introduced by hardware; you can typically set the (negative) offset you would have in osu, or a little bit more
SCALE_OFFSET:   int                = 40  # Introduced by VLC/this script?; Additional offset that scales with the current playback rate
LEAD_SILENCE:   int                = 10_000

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
        # self.pc_t0s contains the list of the last self.n_avg instances of the computed variable pc_t0.
        #
        # When playing media, pc_t0 represents the time at which the media would have started playing
        # without interruption to be at the current state right now.
        # The list is empty whenever the media is paused.
        # 
        # Examples:
        # 
        # - Audio started playing at t0, it is now t1:
        # pc_t0 == t0, since t1 - t0 is the time it took to get there without interruption
        # 
        # - Audio started playing at t0, user skipped 1 second forward at t1, and it is now t2:
        # pc_t0 == t0 - 1000, since it would have taken 1000 more ms to play the media from start to current media time, than the amount of time elapsed since the user actually started playing media
        #
        # - Audio started playing at t0, and user set playing rate to 1.5 at t1 (it is now still t1):
        # pc_t0 == t1 - (t1-t0)/1.5, since it would have taken (t1-t0)/1.5 to reach this point in the media with this rate since the start (instead of (t1-t0)/1.0 for normal playing rate).
        self.pc_t0s: List[int] = []
        self.n_avg:  int       = 3

        # Holds the current media time, in ms, whenever the player is paused, otherwise contains None.
        self.paused_media_time: Optional[int] = 1

        # Boolean indicating whether further user inputs have to be blocked right now
        # (typically used when waiting for player initialization after seeks)
        self.lock: bool = True  # Init to True to wait for player initialization

        self.config_player()

        # Initialize player; make it play for a few seconds, since it is what it needs to have an accurate get_time().
        print("Player initializing...")
        self.play()
        while self.get_media_time() < LEAD_SILENCE:
            time.sleep(0.001)
        self.pause()
        self.lock = False
        print("Player is ready!")

    def get_song_path(self) -> Optional[str]:
        for file in os.listdir(IN_SONG_DIR):
            if file.startswith("[TapRec]") and file.endswith(".mp3"):
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

        timeout = time.perf_counter() + 5.  # In seconds here
        player.play()
        # Wait until the player actually plays audio, waiting only for playing state is not enough
        while time.perf_counter() < timeout:
            if player.get_time() > 0 and player.is_playing():
                self.syncs_since_last_seek = 0
                player.set_time(seek_time)  # Reset the player to the desired time
                self.sync()  # The thread will call sync soon. Also call it here to make sure we have a pc_t0 in time to treat any incoming input.
                self.lock = False
                return
            time.sleep(0.001)

        self.lock = False
        raise RuntimeError("VLC failed to start playback after seek.")

    def change_rate(self, new_rate: float) -> None:
        self.pause()  # Work with actual media time instead of computed, which would cause discontinuity between media time before and after rate change
        media_time = self.get_media_time()
        player.set_rate(new_rate)
        self.seek(media_time)

    def pause(self) -> None:
        self.paused_media_time = self.get_media_time()
        self.pc_t0s[:] = []
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
        # Add it to the list
        self.pc_t0s.append(synced_pc_t0)
        # If we have too many, remove excessive old pc_t0's
        while len(self.pc_t0s) > self.n_avg:
            self.pc_t0s.pop(0)

    def get_media_time(self, pc_t1: Optional[int] = None) -> int:
        if pc_t1 is None:
            pc_t1 = int(time.perf_counter()*1000)

        if not self.pc_t0s:  # In this case, the media is paused; current media time is stored in paused_media_time
            return self.paused_media_time
        
        # Compute pc_t0 current average
        pc_t0_avg = sum(self.pc_t0s) / len(self.pc_t0s)

        return int((pc_t1-pc_t0_avg) * player.get_rate())


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
    clock.seek(max(LEAD_SILENCE, clock.get_media_time() - time))

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
            time        = clock.get_media_time() - LEAD_SILENCE,
            dflt_offset = -int(FLAT_OFFSET + SCALE_OFFSET*player.get_rate()),  # The higher the playing rate, the more consequent the offset will be at 1x speed
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

        print(f"Jumped back to {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}, removing {old_ev_len - new_ev_len} press events.")


    elif key == FWD_KEY:
        if player.is_playing():
            player_go_back(-5000)  # Forward 5 seconds
            print(f"Jumped forward to {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}")

    elif key == SLOWER_KEY:
        if player.is_playing():
            player_incr_rate(-0.1)  # Slower by 10%
            print(f"Decreased playing rate to {round(player.get_rate()*10)/10}")

    elif key == FASTER_KEY:
        if player.is_playing():
            player_incr_rate(0.1)  # Faster by 10%
            print(f"Increased playing rate to {round(player.get_rate()*10)/10}")

    elif key == PLAY_KEY and key == PAUSE_KEY:
        # Same key for pause and play, make it toggle mode
        if player.is_playing():
            clock.pause()
            print(f"Paused at {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}.")
        else:
            clock.play()
            print(f"Playing at {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}...")

    elif key == PLAY_KEY:
        # Different keys for pause and play, treat press as absolute "play" order
        clock.play()
        print(f"Playing at {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}...")

    elif key == PAUSE_KEY:
        clock.pause()
        print(f"Paused at {print_ms_time(clock.get_media_time() - LEAD_SILENCE)}.")


def on_release(key: Key | KeyCode, events: List[PressEvent]) -> None:
    if key in REC_KEYS:
        events.append(PressEvent(
            time        = clock.get_media_time() - LEAD_SILENCE,
            dflt_offset = -int(FLAT_OFFSET + SCALE_OFFSET*player.get_rate()),  # The higher the playing rate, the more consequent the offset will be at 1x speed
            key         = key,
            type        = "release"
        ))


def record() -> List[TapEvent]:
    events: List[PressEvent] = []
    
    with Listener(
            on_press=lambda key : on_press(key, events),
            on_release=lambda key : on_release(key, events)
        ) as listener:
        
        # Start player monitor thread
        threading.Thread(
            target = monitor_player,
            args   = (player, clock, listener),
            daemon = True
        ).start()

        # Start listener
        listener.join()

    return press_to_taps(events)


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
        "dflt_offset": event.dflt_offset,
        "key": serialize_key(event.key)
    }

def serialize_events(events: List[TapEvent]) -> List[Dict[str, Optional[int | str]]]:
    return [serialize_event(event) for event in events]

def print_ms_time(ms: int) -> str:
    minutes = int(ms/(60*1000))
    ms -= minutes*60*1000
    seconds = int(ms/(1000))
    ms -= seconds*1000
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"


# Watches the player.get_time() updates to synchronize the VLCClock object with media time as frequently as possible.
def monitor_player(player: vlc.MediaPlayer, clock: VLCClock, listener: Listener) -> None:
    last_media_time: Optional[int] = None

    while True:
        # Check if player.get_time() has a new value
        cur_media_time: int = player.get_time()
        if last_media_time != cur_media_time:
            clock.sync()
            last_media_time = cur_media_time
        
        # Check for end of audio
        if player.get_state() == vlc.State.Ended:
            print("Reached end of audio, ending recording...")
            listener.stop()  # Simply exit main listener
            return

        time.sleep(0.001)


if __name__ == "__main__":
    # Listen for inputs
    taps = record()

    # Save taps data
    json.dump(serialize_events(taps), open(OUT_PATH, "w"))
    print(f"Saved taps in {OUT_PATH}!")
