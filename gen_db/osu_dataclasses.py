from typing import Optional
from dataclasses import dataclass


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
    map_id: int

    time:         float
    beat_length:  float
    meter:        int  = 4
    sample_set:   int  = 0
    sample_index: int  = 0
    volume:       int  = 100
    unhinerited:  bool = True
    kiai_time:    bool = False


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
    avg_spacing: Optional[float] = None  # Computed average distance spacing for the hit objects in this pattern
    x_start:     Optional[int]   = None  # Computed after insertion
    y_start:     Optional[int]   = None  # Computed after insertion
    x_end:       Optional[int]   = None  # Computed after insertion
    y_end:       Optional[int]   = None  # Computed after insertion
    time_start:  Optional[int]   = None  # Computed after insertion
    time_end:    Optional[int]   = None  # Computed after insertion


@dataclass(kw_only=True)
class Hit_obj:
    id:             Optional[int] = None
    map_id:         int
    pattern_id:     Optional[int] = None
    obj_type_id:    int
    hit_obj_det_id: Optional[int] = None

    x:          int
    y:          int
    time:       int
    hit_sound:  int
    hit_sample: str = "0:0:0:0:"


@dataclass(kw_only=True)
class Hit_obj_det:
    id: int

    curve_data:   Optional[str]   = None
    slides:       Optional[int]   = None
    length:       Optional[float] = None
    edge_sounds:  Optional[str]   = None
    edge_sets:    Optional[str]   = None
    time_end:     Optional[int]   = None  # Computed after insertion for sliders
