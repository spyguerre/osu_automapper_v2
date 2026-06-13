from typing import List
from osu_dataclasses import *
from osu_helper import *
import json
import os
from db_helper import conn
from timing import TP_LIST


TARGET_SR: float = 5.
TARGET_CS: float = 4.2


def pattern_diff_score(candidate: Tuple[Optional[Hit_obj], Hit_obj_list], rec_sample: Tuple[Optional[Hit_obj], Hit_obj_list]) -> Optional[float]:
    # Result/score/cost
    score: float = 0.

    # Readability welp
    prev_ho_c, prev_ho_r = candidate[0], rec_sample[0]
    fst_ho_c, fst_ho_r = candidate[1][0][0], rec_sample[1][0][0]

    # Calc tdelta
    tdelta: int = 0  # Time difference between the start of the two pattern
    if prev_ho_c is None or prev_ho_r is None \
        or fst_ho_c.time - prev_ho_c.time >= 1500 \
        or fst_ho_r.time - prev_ho_r.time >= 1500:
        # Either candidate or rec_sample is first pattern of map, or the time difference between the two patterns is large (1500 ms)
        # In this case, base tdelta on first ho of patterns instead
        tdelta = fst_ho_r.time - fst_ho_c.time
    else:
        # In this case, it makes sense to safely base tdelta on previous ho of patterns
        tdelta = rec_sample[0].time - candidate[0].time
    
    # Adjust candidate ho times knowing tdelta
    if prev_ho_c is not None:
        prev_ho_c.time += tdelta
    for ho_info_c in candidate[1]:
        ho_c, hod_c = ho_info_c
        ho_c.time += tdelta
        if hod_c is not None:
            hod_c.time_end += tdelta
    
    # Calc first distances
    fst_dist_c:    Optional[float] = None  # First distance between previous ho of candidate and first ho of pattern candidate
    fst_dist_r:    Optional[float] = None  # First distance between previous ho of recording and first ho of pattern candidate
    fst_dist_diff: Optional[float] = None  # Absolute difference between fst_dist_c and fst_dist_r if both exist

    # Defines the best transformation to apply to the pattern in order to fit with previous ho,
    # as a tuple representing (horizontal mirror, vertical mirror, x offset, y offset)
    # TODO
    best_transfo: Tuple[bool, bool, float, float] = (False, False, 0., 0.)
    best_transfo_fst_score: Optional[float] = 0

    # Calc both fst_dist
    # fst_dist variables stay None in case they are the first pattern of the map, or the previous ho is more than 1500ms before first ho of pattern
    if prev_ho_c is not None and fst_ho_c.time - prev_ho_c.time <= 1500:
        fst_dist_c = dist((prev_ho_c, None), (fst_ho_c, None))
    if prev_ho_r is not None and fst_ho_c.time - prev_ho_r.time <= 1500:
        fst_dist_r = dist((prev_ho_r, None), (fst_ho_c, None))
    
    ### Compare first distances ###
    if fst_dist_c is not None and fst_dist_r is not None:  # Only compare if both candidate and red patterns have a previous ho that is less than 1500ms before first ho of pattern
        fst_dist_diff = abs(fst_dist_c-fst_dist_r)
        fst_dist_delta_score = 420*(1.042**max(0, fst_dist_diff - 5) - 1)  # Points growing exponentially for each osu!pixel difference above 5 (direction doesn't matter)
        score += fst_dist_delta_score
        if fst_dist_diff > 50:  # Discard candidate if dist diff is greater than 50 osu!pixels
            return None

    # Discard the pattern in case fst_dist_r is set and fst_dist_c isn't
    elif fst_dist_c is None:
        return None

    # Compare stuff in actual pattern now
    for i in range(len(candidate[1])):
        hoi_c, hoi_r = candidate[1][i], rec_sample[1][i]
        ho_c, hod_c  = hoi_c
        ho_r, hod_r  = hoi_r

        ### Compare ho start time ###
        ho_tdelta = ho_r.time - ho_c.time
        
        # Increase score based on time delta for this ho
        ho_tdelta_score = 420*(1.042**max(0, abs(ho_tdelta) - 15) - 1)  # Points growing exponentially for each ms difference above 15
        score += ho_tdelta_score
        if abs(ho_tdelta) > 50:  # Discard candidate if ho tdelta diff is greater than 100ms
            return None
        
        ### Compare ho end time for Sliders / Spinners ###
        if hod_c is not None and hod_r is not None:
            ho_tend_tdelta = hod_r.time_end - hod_c.time_end

            # Increase score based on end time delta for this ho
            ho_tend_tdelta_score = 42*abs(max(0, ho_tend_tdelta - 15))  # Points growing lineraly for each ms difference above 15
            score += ho_tend_tdelta_score

        ### Compare obj type ###
        obj_type_r, obj_type_c = ho_r.obj_type_id, ho_c.obj_type_id
        if obj_type_r != obj_type_c:
            if obj_type_r in {2, 6, 8, 12} and obj_type_c in {1, 5}:
                # Can't convert a candidate Circle to a rec Slider or Spinner, discard candidate pattern
                return None
            # Slightly increase score when candidate ho type doesn't match rec ho type
            score += 300
        
        # Discard pattern if it would create a Spinner that is not long enough
        if (obj_type_c in {8, 12} or obj_type_r in {8, 12} and obj_type_c in {2, 6}) and hod_r and hod_r.time_end - ho_r.time < 1000:
            # Can only accept a candidate Spinner if it is at least 1000ms long
            return None

    score /= (1 + 3*len(candidate[1])-1)  # Favor larger pattern matches
    score /= 100  # Convert to unit scale to compare with tolerance

    return score


def fill_next_coordinates(ho_list: Hit_obj_list, i_ho: int) -> int:
    bpm: float = 60*1000/get_cur_bl(ho_list[i_ho][0].time, TP_LIST)
    
    best_candidate_ho_list:     Optional[Hit_obj_list] = None
    best_candidate_score:       Optional[float]        = None
    best_candidate_backtrack_i: Optional[int]          = None
    tolerance: float = 1.  # Float tolerance threshold that slowly increases linearly, until we find a pattern that suits this threshold
    while best_candidate_score is None or best_candidate_score > tolerance:
        for candidate in conn.select_rd_patterns(
                count=round(100 * (2**(tolerance-1))),
                sr_range=(TARGET_SR-0.2*tolerance, TARGET_SR+0.2*tolerance),
                bpm_range=(bpm-0.1*tolerance, bpm+0.1*tolerance),
                cs_range=(TARGET_CS-0.5*tolerance, TARGET_CS+0.5*tolerance),
                spacing_range=None,
                pat_min_size=round(5-(tolerance-1))
            ):
            # Model the end time and coordinates of the previous hit obj as a Hit Circle
            last_ho_hs_model = None if i_ho == 0 else Hit_obj(
                obj_type_id=1,
                x=ho_list[i_ho-1][0].x if ho_list[i_ho-1][0].obj_type_id not in {2, 6} else get_last_curve_point(ho_list[i_ho-1])[0],
                y=ho_list[i_ho-1][0].y if ho_list[i_ho-1][0].obj_type_id not in {2, 6} else get_last_curve_point(ho_list[i_ho-1])[1],
                time=ho_list[i_ho-1][0].time if ho_list[i_ho-1][1] is None else ho_list[i_ho-1][1].time_end
            )
            # Get the sublist of ho that will be matched with the candidate (same size as candidate, or until end of recording)
            trunc_sample_ho_list = ho_list[i_ho : min(i_ho+len(candidate[1]), len(ho_list))]
            
            rec_sample = (last_ho_hs_model, trunc_sample_ho_list)

            # Truncate candidate pattern's ho_list if it is larger than trunc_sample_ho_list
            candidate = (candidate[0], candidate[1][:min(len(candidate[1]), len(trunc_sample_ho_list))])

            candidate_score = pattern_diff_score(candidate, rec_sample)
            if candidate_score is not None and (best_candidate_score is None or candidate_score < best_candidate_score):
                # Pattern is eligible, and better than the best candidate so far: update best candidate
                best_candidate_ho_list = candidate[1]
                best_candidate_score   = candidate_score

                # Additionally, if this score passes the current tolerance, exit both for and while loops
                if best_candidate_score <= tolerance:
                    break
        
        if best_candidate_score is not None and best_candidate_score <= tolerance:
            break

        # Increase tolerance at each step of the while loop
        tolerance = tolerance + 0.42

    print(f"Using candidate pattern with score = {best_candidate_score:.03f} <= tolerance = {tolerance:.03f} and id = "
          f"{best_candidate_ho_list[0][0].pattern_id} for current HO n°{i_ho}/{len(ho_list)} "
          f"starting at time = {ho_list[i_ho][0].time}")
    # Once we have found a suitable candidate pattern, merge its coordinate data in the next hit objects of our list
    for i_ref, ho_info_ref in enumerate(best_candidate_ho_list):
        ho,     hod     = ho_list[i_ho+i_ref]
        ho_ref, hod_ref = ho_info_ref

        old_obj_type_id = ho.obj_type_id
        ref_obj_type_id = ho_ref.obj_type_id

        new_obj_type_id: Optional[int] = None
        
        # Define new type based on the candidate and desired rec types
        if old_obj_type_id == ref_obj_type_id or old_obj_type_id in {1, 5}:  # Types already match, or rec type is Circle
            # In this case, keep desired rec type
            new_obj_type_id = old_obj_type_id
        
        elif old_obj_type_id in {2, 6}:  # Rec type is Slider and candidate type isn't
            if ref_obj_type_id in {1, 5}:  # Candidate type is a Circle
                raise Exception("Can't convert a candidate Hit Circle into a recording Slider.")
            else:  # Candidate type is a Spinner
                new_obj_type_id = ref_obj_type_id  # Keep candidate Spinner instead of desired rec Slider

        else:  # Rec type is Spinner and candidate type isn't
            if ref_obj_type_id in {1, 5}:
                raise Exception("Can't convert a candidate Hit Circle into a recording Spinner.")
            else:  # Candidate type is a Slider
                new_obj_type_id = old_obj_type_id  # Convert candidate Slider into desired rec Spinner

        ho.x = ho_ref.x
        ho.y = ho_ref.y

        ho.obj_type_id = new_obj_type_id
        if i_ref == 0 and not (ho.obj_type_id >> 2) & 1:  # New combo but new combo bit isn't set in obj type
            ho.obj_type_id += 4
        
        if new_obj_type_id in {8, 12}:  # New type is Spinner
            assert hod_ref and hod.time_end - ho.time >= 1000, "Can't create a Spinner that would be shorter than 1000ms"

        # Depending on the decided new obj type, merge candidate coordinate info into our ho_list that contains the right timings
        if new_obj_type_id in {1, 5}:  # New type is a Circle
            # Remove its corresponding hod if it had one
            hod = None
            ho_list[i_ho+i_ref] = (ho, hod)

        elif new_obj_type_id in {2, 6}:  # New type is a Slider
            assert hod is not None and ref_obj_type_id in {2, 6}, "Type Slider is required for candidate when merging into rec Slider."

            hod.curve_data = hod_ref.curve_data
            hod.slides     = hod_ref.slides
            # Slider length is already computed with timings.
            # However, we previously made the assumption that slides was only 1, which we need to correct if it is now different
            hod.length    /= hod.slides

        else:  # New type is a Spinner
            assert hod is not None and ref_obj_type_id not in {1, 5}, "Type Slider or Spinner is required for candidate when merging into rec Spinner."

            # Remove all unnecessary fields that could previously be set
            hod.curve_data = None
            hod.length     = None
            hod.slides     = None
            # Time_end is already computed with timings for both Slider and Spinner candidate types, and shouldn't be changed here

    # Return the next index of the next ho that has to be filled
    return i_ho + len(best_candidate_ho_list)


def fill_coordinates(ho_list: Hit_obj_list) -> None:
    i_ho: int = 0
    while i_ho < len(ho_list):
        i_ho = fill_next_coordinates(ho_list, i_ho)


if __name__ == "__main__":
    from timing import rec_to_ho_list, cast_ho_list
    recordings: List[dict] = json.load(open(os.path.join("3_record_taps", "recording.json"), "r"))

    rec0 = recordings[-1]
    ho_list = rec_to_ho_list(rec0)
    ho_list = cast_ho_list(ho_list)

    fill_coordinates(ho_list)

    test_gen = "\n".join([f"{ho[0].x},{ho[0].y},{ho[0].time},{ho[0].obj_type_id},0,{"" if ho[0].obj_type_id in {1, 5} else (f"{ho[1].curve_data},{ho[1].slides},{ho[1].length},{"|".join([str(0) for _ in range(ho[1].slides+1)])},{"|".join(["0:0" for _ in range(ho[1].slides+1)])}," if ho[0].obj_type_id in {2, 6} else f"{ho[1].time_end},")}1:0:0:0:" for ho in ho_list])

    import pyperclip
    pyperclip.copy(test_gen)
