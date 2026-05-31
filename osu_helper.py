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


# Get current Slider Velocity Multiplier given the current time and the map's list of timing points
def get_cur_neg_inv_svm(time: int, timing_points: List[Timing_point]) -> int:
    last_inherited_tp = None
    for tp in timing_points:
        if tp.uninherited:  # SVM values are only in inherited TPs
            continue

        if last_inherited_tp is None:
            if time < tp.time:  # Input time is before the first inherited tp
                return -100  # Default value to not change actual slider velocity
            last_inherited_tp = tp
            continue
        
        if time < tp.time:
            return last_inherited_tp.beat_length  # Contains SVM value instead for inherited TPs

    return -100 if last_inherited_tp is None else last_inherited_tp.beat_length  # -100 = default value to not change actual slider velocity


# Get current Beat Length given the current time and the map's list of timing points
def get_cur_bl(time: int, timing_points: List[Timing_point]) -> int:
    last_uninherited_tp = None
    for tp in timing_points:
        if not tp.uninherited:  # BL values are only in uninherited TPs
            continue

        if last_uninherited_tp is None:
            if time < tp.time:  # Input time is before the first uninherited tp
                return timing_points[0].beat_length if timing_points[0].uninherited else 0  # Return first tp's bl if it is uninherited as dflt value, else 0
            last_uninherited_tp = tp
            continue
        
        if time < tp.time:
            return last_uninherited_tp.beat_length

    return (timing_points[0].beat_length if timing_points[0].uninherited else 0) if last_uninherited_tp is None else last_uninherited_tp.beat_length


# Return a tuple containing the current uninherited TP, the current inherited TP and the time until which this information is valid
def get_cur_tps(time: int, timing_points: List[Timing_point]) -> Tuple[Optional[Timing_point], Optional[Timing_point], Optional[int]]:
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
    return res


# Get slider end time knowing its length
def get_slider_end_time(ho_info: Tuple[Hit_obj, Hit_obj_det], map_slider_multiplier: float, tp_list: List[Timing_point]) -> int:
    ho, hod = ho_info
    return ho.time + round(hod.length / (map_slider_multiplier * 100 * (-100/get_cur_neg_inv_svm(ho.time, tp_list))) * get_cur_bl(ho.time, tp_list))


# Get slider length knowing its end time
def get_slider_length(ho_info: Tuple[Hit_obj, Hit_obj_det], map_slider_multiplier: float, tp_list: List[Timing_point]) -> int:
    ho, hod = ho_info
    return round((hod.time_end - ho.time) * map_slider_multiplier * 100 * (-100/get_cur_neg_inv_svm(ho.time, tp_list)) / get_cur_bl(ho.time, tp_list))


# Get coordinates of the last curve point of a slider (takes into account "slides" back-and-forth param)
def get_last_curve_point(hit_obj: Hit_obj, slider: Hit_obj_det) -> Tuple[float, float]:
    if slider.slides % 2 == 0:  # End of slider is its start
        return (hit_obj.x, hit_obj.y)
    
    last_cp: Optional[str] = None
    for curve_data in slider.curve_data.split("|"):
        if ":" in curve_data:
            last_cp = curve_data
    
    return None if last_cp is None else (float(last_cp.split(":")[0]), float(last_cp.split(":")[1]))


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

