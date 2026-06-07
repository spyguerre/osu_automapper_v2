from osu_dataclasses import *
from typing import List, Tuple, Dict


def calc_avg_bpm(timing_points: List[Timing_point], last_ho_time: int) -> float:
    if len(timing_points) == 1:
        return 60*1000/timing_points[0].beat_length  # Formula for BPM
    else:
        intervals:               List[Tuple[float, float]] = []
        last_uninherited_time:   Optional[int]             = None
        last_uninherited_bpm_bl: Optional[int]             = None

        for tp in timing_points:
            if tp.uninherited:  # Only iterate over the uninherited points which contain the beatlength info
                if last_uninherited_time is None:
                    last_uninherited_time   = tp.time
                    last_uninherited_bpm_bl = tp.beat_length
                    continue
                
                intervals.append((
                    tp.time - last_uninherited_time,  # Time between the two timing points
                    60*1000/last_uninherited_bpm_bl   # BPM between the two timing points
                ))

                last_uninherited_time   = tp.time
                last_uninherited_bpm_bl = tp.beat_length

        # Also take into account last inverval defined with the last uninherited tp and last hit object
        intervals.append((
            last_ho_time - last_uninherited_time,  # Time between the two timing points
            60*1000/last_uninherited_bpm_bl   # BPM between the two timing points
        ))

        return sum([ intervals[i][0] * intervals[i][1] for i in range(len(intervals))]) / (last_ho_time - timing_points[0].time)  # BPM average weighted over time


# Return a tuple containing the current uninherited TP, the current inherited TP and the time until which this information is valid
def get_cur_tps(time: int, timing_points: List[Timing_point]) -> Tuple[Optional[Timing_point], Optional[Timing_point], Optional[int]]:
    assert len(timing_points) > 0, "Input timing point list is empty"

    res: Tuple[Optional[Timing_point], Optional[Timing_point], Optional[int]] = (None, None, None)
    for tp in timing_points:
        if tp.time <= time:  # Update current TP depending on its subtype
            if tp.uninherited:
                res = (tp, None, None)  # Uninherited TP invalidates the last inherited TP
            else:
                res = (res[0], tp, None)
        else:  # Reached the first TP after the input time, store its time as our invalidating time and return result
            res = (res[0], res[1], tp.time-1)
            break

    # Attempt to return the first uninhrt tp in case "time" is before the first uninhrt tp's time
    if res[0] is None:
        for tp in timing_points:
            if tp.uninherited:
                res = (tp, res[1],  res[2])
                break

    assert res[0] is not None, "Input timing point list has no uninherited timing point."

    return res


# Get current Slider Velocity Multiplier given the current time and the map's list of timing points
def get_cur_neg_inv_svm(time: int, timing_points: List[Timing_point]) -> int:
    last_inhrt_tp = get_cur_tps(time, timing_points)[1]
    if last_inhrt_tp is None:
        return -100  # Default value to not change actual slider velocity
    else:
        return last_inhrt_tp.beat_length


# Get current Beat Length given the current time and the map's list of timing points
def get_cur_bl(time: int, timing_points: List[Timing_point]) -> int:
    last_uninhrt_tp = get_cur_tps(time, timing_points)[0]

    # This case should not happen since get_cur_tps returns first uninhrt tp if time is before first uninhrt tp, and fails otherwise
    assert last_uninhrt_tp is not None, "Input timing point list has no uninherited timing point."

    return last_uninhrt_tp.beat_length


# Get slider end time knowing its length
def get_slider_end_time(ho_info: Ho_info, map_slider_multiplier: float, tp_list: List[Timing_point]) -> int:
    ho, hod = ho_info
    assert hod is not None, "Input slider \"ho_info\" has no Hit_obj_det."
    return ho.time + round(hod.length / (map_slider_multiplier * 100 * (-100/get_cur_neg_inv_svm(ho.time, tp_list))) * get_cur_bl(ho.time, tp_list))


# Get slider length knowing its end time
def get_slider_length(ho_info: Ho_info, map_slider_multiplier: float, tp_list: List[Timing_point]) -> int:
    ho, hod = ho_info
    assert hod is not None, "Input slider \"ho_info\" has no Hit_obj_det."
    return round((hod.time_end - ho.time) * map_slider_multiplier * 100 * (-100/get_cur_neg_inv_svm(ho.time, tp_list)) / get_cur_bl(ho.time, tp_list))


# Get coordinates of the last curve point of a slider (takes into account "slides" back-and-forth param)
def get_last_curve_point(ho_info: Ho_info) -> Tuple[float, float]:
    hit_obj, slider = ho_info
    
    if slider.slides % 2 == 0:  # End of slider is its start
        return (hit_obj.x, hit_obj.y)
    
    last_cp: Optional[str] = None
    for curve_data in slider.curve_data.split("|"):
        if ":" in curve_data:
            last_cp = curve_data
    
    return None if last_cp is None else (float(last_cp.split(":")[0]), float(last_cp.split(":")[1]))


# Distance between end of ho_info1 and start of ho_info2
def dist(ho_info1: Ho_info, ho_info2: Ho_info) -> float:
    end1 = (ho_info1[0].x, ho_info1[0].y) if ho_info1[1] is None or ho_info1[1].curve_data is None else get_last_curve_point(ho_info1)
    start2 = (ho_info2[0].x, ho_info2[0].y)

    return ((start2[0]-end1[0])**2 + (start2[1]-end1[1])**2)**(1/2)


def serialize_key(key: Key | KeyCode | str) -> Optional[str]:
    if isinstance(key, KeyCode):
        return key.char
    elif isinstance(key, Key):
        return key.name
    elif isinstance(key, str):
        return key
    raise TypeError(f"key '{key}' is of type {type(key)} instead of Key | Keycode | str.")


def serialize_event(event: Tap_event) -> Dict[str, Optional[int | str]]:
    return {
        "time": event.time,
        "time_end": event.time_end,
        "dflt_offset": event.dflt_offset,
        "key": serialize_key(event.key)
    }


def serialize_recordings(recordings: List[List[Tap_event]]) -> List[List[Dict[str, Optional[int | str]]]]:
    return [[serialize_event(event) for event in recording] for recording in recordings]


def print_ms_time(ms: int) -> str:
    minutes = int(ms/(60*1000))
    ms -= minutes*60*1000
    seconds = int(ms/(1000))
    ms -= seconds*1000
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

