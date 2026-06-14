from typing import List
from osu_dataclasses import *
from osu_helper import *
import json
import os
from db_helper import conn
from timing import TP_LIST


TARGET_SR: float = 5.
TARGET_CS: float = 4.2


DIST_TO_PREV_HO_DIFF_THRESHOLD = max(0,  3*(10-TARGET_SR)) + 42  # In osu!pixel
HO_TDELTA_THRESHOLD            = max(0, 10*(10-TARGET_SR)) + 50  # In ms


def pattern_diff_score(candidate: Pat_with_prev_ho, rec_sample: Pat_with_prev_ho, current_best_score: Optional[int]) -> Optional[float]:
    # Result/score/cost
    score: float = 0.
    penalty_multiplier: float = 1.

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
        if fst_dist_diff > DIST_TO_PREV_HO_DIFF_THRESHOLD:  # Discard candidate if dist diff is greater than the threshold
            penalty_multiplier *= 5

    # Score is too big for this pattern already, return None to speed up the process
    if current_best_score and score/1000*penalty_multiplier >= current_best_score:
        return None

    # Discard the pattern in case fst_dist_r is set and fst_dist_c isn't
    elif fst_dist_c is None:
        penalty_multiplier *= 5

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
        if abs(ho_tdelta) > HO_TDELTA_THRESHOLD:  # Discard candidate if ho tdelta diff is greater than the threshold
            penalty_multiplier *= 5
        
        ### Compare ho end time for Sliders / Spinners ###
        if hod_c is not None and hod_r is not None:
            ho_tend_tdelta = hod_r.time_end - hod_c.time_end

            # Increase score based on end time delta for this ho
            ho_tend_tdelta_score = 42*min(35, max(0, ho_tend_tdelta - 15))  # Points growing linearly for each ms difference between 15 and 50
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
        
        # Score is too big for this pattern already, return None to speed up the process
        if current_best_score and score/1000*penalty_multiplier >= current_best_score:
            return None

    score /= (1 + 3*len(candidate[1])-1)  # Encourage larger pattern matches
    score /= 100  # Convert to unit scale to compare with tolerance
    score *= penalty_multiplier

    return score


def fill_next_coordinates(ho_list: Hit_obj_list, i_ho: int) -> int:
    print(f"Looking for pattern to fill at position {i_ho+1: {len(str(len(ho_list)))}d}/{len(ho_list)}...")
    reached_tol_10_msg: bool = False

    bpm: float = 60*1000/get_cur_bl(ho_list[i_ho][0].time, TP_LIST)
    
    best_candidate_ho_list:     Optional[Hit_obj_list] = None
    best_candidate_score:       Optional[float]        = None
    tolerance: float = 1.  # Float tolerance threshold that increases exponentially, until we find a pattern that suits this threshold
    
    # Model the end time and coordinates of the previous hit obj as a Hit Circle
    last_ho_hs_model = None if i_ho == 0 else Hit_obj(
        obj_type_id=1,
        x=ho_list[i_ho-1][0].x if ho_list[i_ho-1][0].obj_type_id not in {2, 6} else get_last_curve_point(ho_list[i_ho-1])[0],
        y=ho_list[i_ho-1][0].y if ho_list[i_ho-1][0].obj_type_id not in {2, 6} else get_last_curve_point(ho_list[i_ho-1])[1],
        time=ho_list[i_ho-1][0].time if ho_list[i_ho-1][1] is None else ho_list[i_ho-1][1].time_end
    )

    # Calc time delta between previous pattern's end time and new pattern start time
    tdelta_to_prev_ho: Optional[int] = None if last_ho_hs_model is None else (ho_list[i_ho][0].time - last_ho_hs_model.time)
    # Calc distance between end of last pattern and start of new pattern
    dist_to_prev_ho: Optional[int] = None if last_ho_hs_model is None else dist((last_ho_hs_model, None), ho_list[0])
    # New pattern's start time
    pat_start_time: int = ho_list[i_ho][0].time

    while best_candidate_score is None or best_candidate_score > tolerance:
        pat_min_size = max(1, round(5-(tolerance-1)))

        # Fetch candidates depending on tolerance and the current map / ho data
        candidates: List[Tuple[Hit_obj, Hit_obj_list]]

        # Tolerance is still low, try to find a pattern that matches more or less perfectly with our needs by using more constraints
        if tolerance < 10:
            candidates = conn.select_rd_patterns(
                count                = 50 + round(tolerance),
                start_prune_pct      = 99 - round(0.5*tolerance),
                max_attempts         = 2 + round(0.3*(tolerance-1)),
                sr_range             = (TARGET_SR - 0.3*tolerance, TARGET_SR + 0.3*tolerance),
                bpm_range            = (      bpm -  5.*tolerance,       bpm +  5.*tolerance),
                cs_range             = (TARGET_CS - 0.3*tolerance, TARGET_CS + 0.3*tolerance),
                spacing_range        = None,  # TODO
                pat_min_size         = pat_min_size,
                to_prev_tdelta_range = (tdelta_to_prev_ho - round( 5*tolerance), tdelta_to_prev_ho + round( 5*tolerance)) if tdelta_to_prev_ho is not None else None,
                to_prev_dist_range   = (  dist_to_prev_ho - round(10*tolerance),   dist_to_prev_ho + round(10*tolerance)) if dist_to_prev_ho   is not None else None,
                search_anchor_ho     = last_ho_hs_model if dist_to_prev_ho is not None else None,
                to_fst_tdelta_ranges = [
                    (
                        ho_list[l_i_ho][0].time - pat_start_time - round(5*tolerance),
                        ho_list[l_i_ho][0].time - pat_start_time + round(5*tolerance)
                    )
                    for l_i_ho in range(i_ho, min(len(ho_list), pat_min_size))
                ]
            )

        # Tolerance is already high which means there might not be any result with the constraints above;
        # try to find a random pattern that eventually satisfies the tolerance to avoid looping indefinitely
        else:
            if not reached_tol_10_msg:
                print("Reached tolerance = 10 for this pattern.")
                reached_tol_10_msg = True

            candidates = conn.select_rd_patterns(
                count                = 50 + round(tolerance),
                start_prune_pct      = 99,
                max_attempts         = 2,
                sr_range             = (TARGET_SR -  3*(tolerance-7), TARGET_SR +  1*(tolerance-7)),
                bpm_range            = (      bpm - 10*(tolerance-5),       bpm + 10*(tolerance-5))
            )
        
        for candidate in candidates:
            # Get the sublist of ho that will be matched with the candidate (same size as candidate, or until end of recording)
            trunc_sample_ho_list = ho_list[i_ho : min(i_ho+len(candidate[1]), len(ho_list))]
            
            rec_sample = (last_ho_hs_model, trunc_sample_ho_list)

            # Truncate candidate pattern's ho_list if it is larger than trunc_sample_ho_list
            candidate = (candidate[0], candidate[1][:min(len(candidate[1]), len(trunc_sample_ho_list))])

            candidate_score = pattern_diff_score(candidate, rec_sample, best_candidate_score)
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
        tolerance = tolerance + 0.42*tolerance

    print(f"""Found matching pattern for Hit Objects  {i_ho+1: {len(str(len(ho_list)))}d}/{len(ho_list)} ==> {i_ho+len(best_candidate_ho_list): {len(str(len(ho_list)))}d}/{len(ho_list)}:
- Score     = {best_candidate_score: 8.2f}
- Tolerance = {tolerance: 8.2f}
- ID        = {best_candidate_ho_list[0][0].pattern_id: 8d} 
- Length    = {len(best_candidate_ho_list): 8d}
- Time      = {ho_list[i_ho][0].time: 8d}
""")
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
    if not (best_candidate_score is None or best_candidate_score > tolerance):
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
