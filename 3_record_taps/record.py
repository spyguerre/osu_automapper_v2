from pynput.keyboard import Key, KeyCode, Listener
import json
from typing import List, Literal, Set, Optional, Dict, Tuple
import os
import vlc
import time
import threading
from osu_dataclasses import Press_event, Tap_event
from osu_helper import serialize_recordings, print_ms_time


LEAD_SILENCE:   int                = 10_000
VOLUME:         int                = 42  # Volume of the playback as an integer percentage
RATE:           float              = 1.  # Default playback rate

REC_KEYS:       Set[Key | KeyCode] = {KeyCode.from_char("e"), KeyCode.from_char("r")}
BACK_KEY:       Key | KeyCode      = Key.left
FWD_KEY:        Key | KeyCode      = Key.right
SLOWER_KEY:     Key | KeyCode      = Key.down
FASTER_KEY:     Key | KeyCode      = Key.up
PLAY_KEY:       Key | KeyCode      = Key.space
PAUSE_KEY:      Key | KeyCode      = Key.space
QUIT_KEY:       Key | KeyCode      = Key.esc

IN_SONG_DIR:    str                = "3_record_taps"
OUT_PATH:       str                = os.path.join(IN_SONG_DIR, "recording.json")


class Recorder():
    def __init__(self, song_fp: Optional[str] = None, volume: Optional[int] = None, rate: Optional[float] = None) -> None:
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

        # Init VLC Instance and Player
        self.vlc_instance: vlc.Instance    = vlc.Instance("--file-caching=50")
        self.player:       vlc.MediaPlayer = self.vlc_instance.media_player_new()

        self.config_player(song_fp=song_fp, volume=volume, rate=rate)
        
        # The list of Press Events that is going to be recorded
        self.events: List[Press_event] = []

        # Initialize player; make it play for a few seconds, since it is what it needs to have an accurate get_time().
        print("Player initializing...")
        self.play()
        while self.get_media_time() < LEAD_SILENCE:
            time.sleep(0.001)
        self.pause()
        self.lock = False
        print("Player is ready. Hit play whenever you're ready!")

    def get_song_path(self) -> Optional[str]:
        for file in os.listdir(IN_SONG_DIR):
            if file.startswith("[TapRec]") and file.endswith(".mp3"):
                return os.path.join(IN_SONG_DIR, file)

    def config_player(self, song_fp: Optional[str] = None, volume: Optional[int] = None, rate: Optional[float] = None) -> None:
        # Fill default arguments
        song_fp = song_fp if song_fp is not None else self.get_song_path()
        volume = volume if volume is not None else VOLUME
        rate = rate if rate is not None else RATE

        # Load media
        media = self.vlc_instance.media_new(song_fp)
        self.player.set_media(media)

        # Ensure correct load of media
        assert self.player.get_media() is not None
        assert self.player.get_media().get_mrl() is not None

        # Custom player params
        self.player.audio_set_volume(volume)
        self.player.set_rate(rate)


    def seek(self, seek_time: int) -> None:
        self.lock = True

        timeout = time.perf_counter() + 5.  # In seconds here
        self.player.play()
        # Wait until the player actually plays audio, waiting only for playing state is not enough
        while time.perf_counter() < timeout:
            if self.player.get_time() > 0 and self.player.is_playing():
                self.syncs_since_last_seek = 0
                self.player.set_time(seek_time)  # Reset the player to the desired time
                self.sync()  # The thread will call sync soon. Also call it here to make sure we have a pc_t0 in time to treat any incoming input.
                self.lock = False
                return
            time.sleep(0.001)

        self.lock = False
        raise RuntimeError("VLC failed to start playback after seek.")

    def change_rate(self, new_rate: float) -> None:
        self.pause()  # Work with actual media time instead of computed, which would cause discontinuity between media time before and after rate change
        media_time = self.get_media_time()
        # Rate 1.0 has a lot less latency (~40ms); align on modified rate latency with additional .0001. This allows for consistent recording offset, no matter the playback rate!
        self.player.set_rate(new_rate if new_rate != 1. else 1.0001)
        self.seek(media_time)


    def pause(self) -> None:
        self.paused_media_time = self.get_media_time()
        self.pc_t0s[:] = []
        if self.player.is_playing():
            self.player.pause()

    def play(self) -> None:
        self.seek(self.paused_media_time)
        self.paused_media_time = None


    def sync(self) -> None:
        # Since this method is only called whenever the media time was just updated,
        # we can synchronize cur_pc_time to the media_time (which is, right now only, ground truth)
        cur_media_time = self.player.get_time()
        cur_pc_time = time.perf_counter()*1000
        
        player_rate = self.player.get_rate()
        
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

        return int((pc_t1-pc_t0_avg) * self.player.get_rate())


    def player_go_back(self, time: int = 5000) -> None:
        self.seek(max(LEAD_SILENCE, self.get_media_time() - time))

    def player_incr_rate(self, rate: float = 0.1) -> None:
        self.change_rate(self.player.get_rate() + rate)

    def on_press(self, key: Key | KeyCode) -> Optional[Literal[False]]:
        # First check if user wants to quit
        if key == QUIT_KEY:
            return False  # Exit recording
        
        # If recorder is already treating a player action, drop the user event until audio is playing properly again
        if self.lock:
            return
        
        # Treat user event
        if key in REC_KEYS:
            self.events.append(Press_event(
                time        = self.get_media_time() - LEAD_SILENCE,
                key         = key,
                type        = "press"
            ))

        elif key == BACK_KEY:
            if not self.player.is_playing():
                return
            
            ms_amount: int = 5000

            # Additionally, remove all press events of type "press" in the event list
            pc_cur_time = int(time.perf_counter()*1000)
            cur_time = self.get_media_time(pc_cur_time)
            back_time = max(LEAD_SILENCE, self.get_media_time(pc_cur_time - ms_amount))  # Compute with self.get_media_time to take into account playing rate
            old_ev_len = len(self.events)
            self.events[:] = [event for event in self.events if not (back_time <= event.time+LEAD_SILENCE <= cur_time and event.type == "press")]
            new_ev_len = len(self.events)

            self.player_go_back(ms_amount)  # Back 5 seconds

            print(f"Jumped back to {print_ms_time(back_time - LEAD_SILENCE)}, removing {old_ev_len - new_ev_len} press events.")

        elif key == FWD_KEY:
            if self.player.is_playing():
                self.player_go_back(-5000)  # Forward 5 seconds
                print(f"Jumped forward to {print_ms_time(self.get_media_time() - LEAD_SILENCE)}")

        elif key == SLOWER_KEY:
            if self.player.is_playing():
                self.player_incr_rate(-0.1)  # Slower by 10%
                print(f"Decreased playing rate to {round(self.player.get_rate()*10)/10}")

        elif key == FASTER_KEY:
            if self.player.is_playing():
                self.player_incr_rate(0.1)  # Faster by 10%
                print(f"Increased playing rate to {round(self.player.get_rate()*10)/10}")

        elif key == PLAY_KEY and key == PAUSE_KEY:
            # Same key for pause and play, make it toggle mode
            if self.player.is_playing():
                self.pause()
                print(f"Paused at {print_ms_time(self.get_media_time() - LEAD_SILENCE)}.")
            else:
                self.play()
                print(f"Playing at {print_ms_time(self.get_media_time() - LEAD_SILENCE)}...")

        elif key == PLAY_KEY:
            # Different keys for pause and play, treat press as absolute "play" order
            self.play()
            print(f"Playing at {print_ms_time(self.get_media_time() - LEAD_SILENCE)}...")

        elif key == PAUSE_KEY:
            self.pause()
            print(f"Paused at {print_ms_time(self.get_media_time() - LEAD_SILENCE)}.")


    def on_release(self, key: Key | KeyCode) -> None:
        if key in REC_KEYS:
            self.events.append(Press_event(
                time        = self.get_media_time() - LEAD_SILENCE,
                key         = key,
                type        = "release"
            ))


    def record(self) -> List[Tap_event]:
        with Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
            
            # Start player monitor thread
            threading.Thread(
                target = self.monitor_player,
                args   = (listener,),
                daemon = True
            ).start()

            # Start listener
            listener.join()

        return self.press_to_taps()


    def press_to_taps(self) -> List[Tap_event]:
        press_dict: Dict[Key | KeyCode, int] = {}
        res: List[Tap_event] = []
        for event in self.events:
            match event.type:
                case "press":
                    if event.key in press_dict.keys():  # Ignore repeated press events that are never released (happens when holding press usually)
                        continue
                    press_dict[event.key] = event.time

                case "release":
                    if event.key not in press_dict.keys():  # Ignore release events that have no corresponding press events (can happen when pressing back)
                        continue
                    press_info = press_dict.pop(event.key)
                    res.append(Tap_event(
                        time        = press_info,
                        time_end    = event.time,
                        key         = event.key
                    ))
        return res


    # Watches the self.player.get_time() updates to synchronize the Recorder object with media time as frequently as possible.
    def monitor_player(self, listener: Listener) -> None:
        last_media_time: Optional[int] = None

        while True:
            # Check if self.player.get_time() has a new value
            cur_media_time: int = self.player.get_time()
            if last_media_time != cur_media_time:
                self.sync()
                last_media_time = cur_media_time
            
            # Check for end of audio
            if self.player.get_state() == vlc.State.Ended:
                print("Reached end of audio, ending recording...")
                listener.stop()  # Simply exit main listener
                return

            time.sleep(0.001)


if __name__ == "__main__":
    # Instanciate our Recorder object
    recorder: Recorder = Recorder()

    # Listen for inputs
    try:
        rec = recorder.record()
    except KeyboardInterrupt:
        print("Discarded recording.")
        exit()
    
    # Save taps data
    recordings: List[List[Tap_event]] = []
    if os.path.isfile(OUT_PATH):
        recordings[:] = [[Tap_event(**tap) for tap in recording] for recording in json.load(open(OUT_PATH, "r"))]
    recordings.append(rec)
    json.dump(serialize_recordings(recordings), open(OUT_PATH, "w"))
    print(f"Saved new recording in {OUT_PATH}! (Now {len(recordings)} recording(s)).")
