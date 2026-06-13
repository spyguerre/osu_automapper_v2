from typing import List, Dict
from osu_dataclasses import *
from osu_helper import *
import json
import os


DFLT_REC_OFFSET: int = -147  # Easily find this value with the 3_record_taps/calibration.py script!

TP_LIST: List[Timing_point] = [
    Timing_point(
        time         = 1685,
        beat_length  = 60*1000 / 140,  # 140 BPM to beat_length
        meter        = 12,  # The possible subdivisions for this TP. You should put the smallest meter nummber that corresponds to ALL the measures in this TP. In my example, I need both standard (meter=4) and triplets (meter=3) subdivisions, so I go for 12.
        sample_set   = 0,
        sample_index = 0,
        volume       = 42,
        uninherited  = True,
        kiai_time    = False,
        rec_offset   = 0
    )
]

# Used to map the beat subdivisions (1/1, 1/2, 1/4...) to the time window (in proportion of a beat; e.g. 0.25 for a fourth of a beat) accepted for a cast.
CAST_WINDOWS: Dict[int, float] = {
    1:  2./10.,
    2:  2./10.,
    3:  2./14.,
    4:  1./4.,
    8:  1./8.,
    16: 1./16.,
}

# How many beats long a tap event needs to be in order to be made a slider/spinner instead of a circle
SLIDER_THRESHOLD:  float = 1./3.
SPINNER_THRESHOLD: float = 3. + 1./2.

# By how many beats the end time of a spinner/slider should be at least separated from the start of the next hit object
END_TIME_MIN_SPACING: float = 1./4.

# Map parameter controling slider velocity. Osu's default is 1.4
MAP_SLIDER_MULTIPLIER: float = 1.4


def get_last_beat(time: int, cur_uninhrt_tp: Timing_point) -> int:
    bl = cur_uninhrt_tp.beat_length
    tp_time = cur_uninhrt_tp.time
    return round(((time - tp_time) // bl) * bl + tp_time)


def get_cast_time(time: int, last_beat: int, cur_bl: float, cur_meter: int) -> Optional[int]:
    for subdiv, window in CAST_WINDOWS.items():
        if cur_meter % subdiv != 0:  # Current meter doesn't allow this subdiv
            continue

        if subdiv == 3 and cur_meter % 4 == 0:  # Already treated this case above
            continue
        
        # Iterate over all the possible cast times for this subdiv
        for subdiv_i in range(subdiv + 1):  # +1 to also allow casting to next full beat
            cast_time = round(last_beat + cur_bl*subdiv_i/subdiv)
            # Check if ho is in the cast window
            if abs(time - cast_time) < cur_bl*window/2:
                return cast_time
    
    return None  # When we couldn't find a fitting cast


def cast_ho_list(ho_list: Hit_obj_list) -> Hit_obj_list:
    if not ho_list:
        return []

    tp_info_valid_until: Optional[int]          = 0  # Is None when valid until the end
    cur_uninhrt_tp:      Optional[Timing_point] = None
    cur_bl:              Optional[float]        = None
    cur_meter:           Optional[int]          = None

    triplets_cast_mem:   Optional[int]          = None  # Remembers the last matched triplet that we cast

    for i_ho, ho_info in enumerate(ho_list):
        ho = ho_info[0]
        cast_happened: bool = False
        
        # Renew tp info only if we need to
        if tp_info_valid_until is not None and tp_info_valid_until < ho.time:
            cur_uninhrt_tp, _, tp_info_valid_until = get_cur_tps(ho.time, TP_LIST)
            if cur_uninhrt_tp is not None:
                cur_bl    = cur_uninhrt_tp.beat_length
                cur_meter = cur_uninhrt_tp.meter
            else:  # Tap is before first timing point
                if TP_LIST[0].uninherited:  # Retrieve info from first tp if it is uninherited
                    cur_uninhrt_tp = TP_LIST[0]
                    cur_meter      = TP_LIST[0].meter
                    cur_bl         = TP_LIST[0].beat_length
                else:  # Else just skip this tap
                    continue
        
        last_beat = get_last_beat(ho.time, cur_uninhrt_tp)
        next_beat = round(last_beat + cur_bl)
        
        # First, try to cast ho times to triplets in the case that the current meter allows both 1/3s and 1/4s
        # In this case, we prefer to only cast ho to 1/3s if there are two ho's in this beat that can be cast to both of the beat's 1/3s
        if cur_meter % 3 == 0 and cur_meter % 4 == 0:
            if abs(ho.time - (last_beat + cur_bl*1/3)) < cur_bl*CAST_WINDOWS[3]/2:  # Ho is in the cast window of the BEAT'S FIRST 1/3
                match:   Optional[Hit_obj] = None  # The ho match for the beat's second 1/3 if next HO fits
                i_match: int               = i_ho + 1
                if i_match < len(ho_list):
                    match_candidate = ho_list[i_match][0]

                    if abs(match_candidate.time - (last_beat + cur_bl*2/3)) < cur_bl*CAST_WINDOWS[3]/2:  # Match_candidate is in the cast window of the BEAT'S SECOND 1/3
                        match = match_candidate

                # Discard match in case there is another HO strictly within last_beat and next_beat
                l_i_ho = 0
                while l_i_ho < len(ho_list):
                    l_ho = ho_list[l_i_ho][0]

                    if l_ho.time < last_beat:  # Ignore ho's before last_beat
                        l_i_ho += 1
                        continue
                    if abs(l_ho.time - last_beat) < cur_bl*CAST_WINDOWS[1]/2:  # Ignore ho's that could be cast to last_beat
                        l_i_ho += 1
                        continue
                    if l_i_ho in (i_ho, i_match):  # Ignore current ho and match candidate
                        l_i_ho += 1
                        continue
                    if abs(l_ho.time - next_beat) < cur_bl*CAST_WINDOWS[1]/2:  # Pass if we reach an ho that could be cast to next_beat
                        break
                    if l_ho.time > next_beat:  # Pass if we reach an ho that is after next_beat
                        break

                    # Fail match otherwise, turn it back to None
                    match = None
                    break

                if match:  # If we found a match, cast both their own 1/3
                    ho.time           = round(last_beat + cur_bl*1/3)
                    match.time        = round(last_beat + cur_bl*2/3)
                    triplets_cast_mem = i_match
                    cast_happened     = True

            elif i_ho == triplets_cast_mem:  # Prevents casting this ho again
                triplets_cast_mem = None
                cast_happened     = True

        # Then, attempt casting the current ho to the most to least significant subdiv
        if not cast_happened:
            cast_time = get_cast_time(ho.time, last_beat, cur_bl, cur_meter)
            if cast_time is not None:
                ho.time = cast_time
                cast_happened = True
    
    # Remove duplicates
    res = [ho_list[0]] + [ho_list[i] for i in range(1, len(ho_list)) if abs(ho_list[i][0].time - ho_list[i-1][0].time) >= 2]

    # Now that we've cast all hit obj start times, also cast the sliders' length and spinners' end time
    tp_info_valid_until = 0
    for i_ho, ho_info in enumerate(res):
        ho, hod = ho_info

        # Renew tp info only if we need to
        if tp_info_valid_until is not None and tp_info_valid_until < ho.time:
            cur_uninhrt_tp, _, tp_info_valid_until = get_cur_tps(ho.time, TP_LIST)
            if cur_uninhrt_tp is not None:
                cur_bl    = cur_uninhrt_tp.beat_length
                cur_meter = cur_uninhrt_tp.meter
            else:  # Tap is before first timing point
                if TP_LIST[0].uninherited:  # Retrieve info from first tp if it is uninherited
                    cur_uninhrt_tp = TP_LIST[0]
                    cur_meter      = TP_LIST[0].meter
                    cur_bl         = TP_LIST[0].beat_length
                else:  # Else just skip this tap
                    continue

        if ho.obj_type_id in {1, 5}:  # Circle
            continue
        assert hod is not None, f"Input hit object of type {ho.obj_type_id} has no Hit_obj_det."

        # Start by limiting the end time of both object types, so that they don't overlap with the next hit object with a small margin
        if i_ho < len(res) - 1:  # Ensure there is a next object
            hod.time_end = min(hod.time_end, round(res[i_ho+1][0].time - cur_bl*END_TIME_MIN_SPACING))

        last_beat = get_last_beat(hod.time_end, cur_uninhrt_tp)

        # Perform cast for end time
        cast_time_end = get_cast_time(hod.time_end, last_beat, cur_bl, cur_meter)
        if cast_time_end is not None:
            hod.time_end = cast_time_end

            # Check that the start and end time of the ho are spaced by at least 3/4 of the slider threshold, else just turn the ho back into a circle
            if hod.time_end - ho.time < 0.75*SLIDER_THRESHOLD*cur_bl:
                ho.obj_type_id -= (1 if ho.obj_type_id in {2, 6} else 7)
                res[i_ho] = (ho, None)

        # Compute new length for sliders
        if ho.obj_type_id in {2, 6}:  # Slider
            hod.length = get_slider_length((ho, hod), MAP_SLIDER_MULTIPLIER, TP_LIST)

    return res


# Builds an initial list of Hit objects knowing recording data
def rec_to_ho_list(recording: List[dict]) -> Hit_obj_list:
    events: List[Tap_event] = [Tap_event(**event_dict) for event_dict in recording]

    tp_info_valid_until: Optional[int]          = 0  # Is None when valid until the end
    cur_uninhrt_tp:      Optional[Timing_point] = None
    cur_inhrt_tp:        Optional[Timing_point] = None
    cur_rec_offset:      int                    = 0
    cur_bl:              Optional[float]        = None

    res = []
    for event in events:
        # Renew tp info only if we need to
        if tp_info_valid_until is not None and tp_info_valid_until < event.time:
            cur_uninhrt_tp, cur_inhrt_tp, tp_info_valid_until = get_cur_tps(event.time, TP_LIST)
            if cur_uninhrt_tp is not None:
                cur_rec_offset = cur_uninhrt_tp.rec_offset
                cur_bl         = cur_uninhrt_tp.beat_length

            if cur_inhrt_tp is not None:
                cur_rec_offset = cur_inhrt_tp.rec_offset

        if cur_bl is None:  # Tap is before first timing point
            if TP_LIST[0].uninherited:  # Default to first TP's BL if it is uninherited
                cur_bl = TP_LIST[0].beat_length
            else:  # Else just ignore the tap
                continue

        tap_duration = event.time_end - event.time
        
        obj_type_id: Optional[int]         = None
        hod:         Optional[Hit_obj_det] = None
        if tap_duration < SLIDER_THRESHOLD*cur_bl:
            obj_type_id = 1  # Circle
        elif SLIDER_THRESHOLD*cur_bl <= tap_duration < SPINNER_THRESHOLD*cur_bl:
            obj_type_id = 2  # Slider
            hod = Hit_obj_det(
                curve_data = "L|257:193",
                slides     = 1,
                length     = 42.,
                time_end   = event.time_end + DFLT_REC_OFFSET + cur_rec_offset
            )
        else:
            obj_type_id = 8  # Spinner
            hod = Hit_obj_det(
                time_end = event.time_end + DFLT_REC_OFFSET + cur_rec_offset
            )

        ho = Hit_obj(
            obj_type_id = obj_type_id,
            x           = 256,
            y           = 192,
            time        = event.time + DFLT_REC_OFFSET + cur_rec_offset,
            hit_sound   = 0
        )

        res.append((ho, hod))
    
    return res


if __name__ == "__main__":
    recordings: List[dict] = json.load(open(os.path.join("3_record_taps", "recording.json"), "r"))
    
    rec0 = recordings[-1]
    ho_list = rec_to_ho_list(rec0)
    ho_list = cast_ho_list(ho_list)
    test_gen = "\n".join([f"{ho[0].x},{ho[0].y},{ho[0].time},{ho[0].obj_type_id},0,{"" if ho[0].obj_type_id in {1, 5} else (f"{ho[1].curve_data},{ho[1].slides},{ho[1].length},{"|".join([str(0) for _ in range(ho[1].slides+1)])},{"|".join(["0:0" for _ in range(ho[1].slides+1)])}," if ho[0].obj_type_id in {2, 6} else f"{ho[1].time_end},")}1:0:0:0:" for ho in ho_list])

    import pyperclip
    pyperclip.copy(test_gen)
