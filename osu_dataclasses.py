from typing import Optional, Literal, List, Tuple
from dataclasses import dataclass
from pynput.keyboard import Key, KeyCode


@dataclass(kw_only=True)
class Beatmapset:
    id: Optional[int] = None  # Osu! Beatmapset ID

    title:      str
    artist:     str
    creator:    str
    play_count: int


@dataclass(kw_only=True)
class Beatmap:
    # Keys
    id:     Optional[int] = None  # Osu! Beatmap Difficulty ID
    set_id: Optional[int] = None

    # General info
    star_rating: Optional[float] = None  # Computed after insertion
    avg_bpm:     Optional[float] = None  # Computed after insertion
    file_name:   str
    file_format: Optional[int]   = None

    # Map metadata
    title:          Optional[str] = None
    title_unicode:  Optional[str] = None
    artist:         Optional[str] = None
    artist_unicode: Optional[str] = None
    creator:        Optional[str] = None
    diff_name:      Optional[str] = None
    source:         Optional[str] = None
    tags:           Optional[str] = None

    # Difficulty settings
    hp_drain_rate:      float = 5.
    circle_size:        float = 5.
    overall_difficulty: float = 5.
    approach_rate:      float = 5.
    slider_multiplier:  float = 1.4
    slider_tick_rate:   float = 1.

    # Misc settings
    audio_filename:              Optional[str] = None
    audio_lead_in:               int           = 0
    preview_time:                int           = -1
    countdown:                   int           = 1
    sample_set:                  str           = "Normal"
    stack_leniency:              float         = 0.7
    letterbox_in_breaks:         bool          = False
    use_skin_sprites:            bool          = False
    overlay_position:            str           = "NoChange"
    skin_preference:             Optional[str] = None
    epilepsy_warning:            bool          = False
    countdown_offset:            int           = 0
    widescreen_storyboard:       bool          = False
    samples_match_playback_rate: bool          = False


@dataclass(kw_only=True)
class Timing_point:
    id:     Optional[int] = None
    map_id: Optional[int] = None

    time:         float
    beat_length:  float
    meter:        int  = 4
    sample_set:   int  = 0
    sample_index: int  = 0
    volume:       int  = 100
    uninherited:  bool = True
    kiai_time:    bool = False

    rec_offset:   int  = 0  # Custom offset applied in addition to the default offset stored in Tap_events


@dataclass(kw_only=True)
class Event:
    id:            Optional[int] = None
    map_id:        int
    event_type_id: Optional[int] = None

    time_start:   Optional[int] = None
    file_name:    Optional[str] = None
    x_offset:     Optional[int] = None
    y_offset:     Optional[int] = None
    time_end:     Optional[int] = None
    event_params: Optional[str] = None


@dataclass(kw_only=True)
class Pattern:
    id: Optional[int]     = None
    map_id: int

    duration:    Optional[float] = None  # Computed time duration from the first to the end of the last hit object in this pattern
    size:        Optional[int]   = None  # Computed count of hit objects in this pattern (sliders count for their number of "slides" + 1)
    avg_spacing: Optional[float] = None  # Computed average distance spacing for the hit objects in this pattern (osu!pixel dist / time delta)
    x_start:     Optional[int]   = None  # Computed after insertion
    y_start:     Optional[int]   = None  # Computed after insertion
    x_end:       Optional[int]   = None  # Computed after insertion
    y_end:       Optional[int]   = None  # Computed after insertion
    time_start:  Optional[int]   = None  # Computed after insertion


@dataclass(kw_only=True)
class Hit_obj:
    id:             Optional[int] = None
    map_id:         Optional[int] = None
    pattern_id:     Optional[int] = None
    obj_type_id:    int
    hit_obj_det_id: Optional[int] = None

    x:          int
    y:          int
    time:       Optional[int] = None
    hit_sound:  int           = 0
    hit_sample: str           = "0:0:0:0:"

    map_obj_nr:     Optional[int] = None  # Computed after insertion
    pattern_obj_nr: Optional[int] = None  # Computed after insertion


@dataclass(kw_only=True)
class Hit_obj_det:
    id: Optional[int] = None

    curve_data:   Optional[str]   = None
    slides:       Optional[int]   = None
    length:       Optional[float] = None
    edge_sounds:  Optional[str]   = None
    edge_sets:    Optional[str]   = None
    time_end:     Optional[int]   = None  # Computed after insertion for sliders


# Class representing a single keyboard event: pressing or releasing a key
@dataclass(kw_only=True)
class Press_event:
    time:         int                          # Time in ms from start of recording
    key:          Key | KeyCode                # The key pressed or released
    type:         Literal["press", "release"]  # Whether event is a press (True) or a release (False) event


# Class representing a tap event: both press and release of a key
@dataclass(kw_only=True)
class Tap_event:
    time:         int                  # In ms
    time_end:     int                  # In ms
    key:          Key | KeyCode | str  # The key pressed and released


# Additional types
Ho_info = Tuple[Hit_obj, Optional[Hit_obj_det]]
Hit_obj_list = List[Ho_info]
Recording = List[Tap_event]
Pat_with_prev_ho = Tuple[Optional[Hit_obj], Hit_obj_list]
