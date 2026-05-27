import os
from osu_dataclasses import *
import json
from db_helper import Db_conn
from osu_sr_calculator import calculateStarRating
from typing import List, Tuple
import warnings
from osu_helper import calc_avg_bpm, get_cur_neg_inv_svm, get_cur_bl, get_last_curve_point


MAP_LIST_PATH = "dataset/maps/"
BEATMAPS_JSON_PATH = os.path.join("1_download_maps", "beatmapsets.json")

EVENT_TYPE_MAP = {
    "0": 0,
    "Background": 0,
    "1": 1,
    "Video": 0,
    "2": 2,
    "Break": 2
}


def init_schema():
    print("Creating tables...")
    conn = Db_conn()
    conn.init_schema()
    conn.commit()
    conn.close()
    print("Done creating tables.\n")


def add_beatmapsets_json_data():
    conn = Db_conn()

    print("Inserting sets...")

    # Insert all sets
    beatmapsets = json.load(open(BEATMAPS_JSON_PATH, "r"))
    for set_dict in beatmapsets:
        set = Beatmapset(
            id=set_dict["id"],
            title=set_dict["title"],
            artist=set_dict["artist"],
            creator=set_dict["creator"],
            play_count=set_dict["play_count"]
        )
        conn.insert_set(set)

    conn.commit()

    print("Done inserting sets.\n")

    conn.close()


def add_osu_files_data():
    # Instanciate connection
    conn = Db_conn()

    print("Inserting data from osu files...")

    map_dir = os.listdir(MAP_LIST_PATH)
    map_cnt = len(map_dir)
    # Read each .osu file to retrieve the other object types
    for file_i, file in enumerate(map_dir):
        print(f"Processing file {file_i + 1}/{map_cnt}: {''.join(filter(str.isascii, file))}...")

        lines = open(os.path.join(MAP_LIST_PATH, file), "r", encoding="UTF-8").readlines()

        section: Optional[str] = None
        last_pattern_id: Optional[int] = None
        map = Beatmap(file_name=file)
        is_standard_mode_map: bool = None
        pattern: Optional[Pattern] = None
        cur_map_obj_nr: int = 0
        map_timing_points: List[Timing_point] = []
        cur_pattern_ho_extn: List[Tuple[Hit_obj, Optional[Hit_obj_det]]] = []
        map_last_ho_time: Optional[int] = None

        for line in lines:
            if is_standard_mode_map is False:  # Don't care about mania or taiko difficulties here
                break

            line = line.strip()  # We love Windows \r\n

            line = line.split("//")[0]  # Ignore comments

            line = line.replace("\ufeff", "")  # Why would this thing even be there in the first place???

            # Empty lines
            if not line:
                continue
            
            # Update section
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]

                if section == "Events":  # No more map-related data from now on, so we insert the map object in db
                    if map.set_id is None:  # If set id wasn't specified in .osu file, fetch it from beatmapset table
                        res = conn.select(
                            table="beatmapset",
                            dict={"artist": f"'{map.artist.replace("'", "''")}'", "title": f"'{map.title.replace("'", "''")}'", "creator": f"'{map.creator}'"},
                            cols=["id"],
                            limit=1
                        )
                        if not res:  # If we can't find a corresponding beatmapset, it's probably because the creator changed their name
                            # Fallback to searching without creator name, even if we end up picking the wrong beatmapset
                            res = conn.select(
                            table="beatmapset",
                            dict={"artist": f"'{map.artist.replace("'", "''")}'", "title": f"'{map.title.replace("'", "''")}'"},
                            cols=["id"],
                            limit=1
                        )
                        map.set_id = res[0]["id"]
                    
                    # Fill unicode fields with default fields if they are not specified
                    if not map.title_unicode:
                        map.title_unicode = map.title
                    if not map.artist_unicode:
                        map.artist_unicode = map.artist

                    # In case we don't have a map id in the metadata (or it is set to 0 for some reason.....), let the db create a random one :/
                    if map.id == 0:
                        map.id = None

                    map.id = conn.insert_map(map)

                continue

            # General
            match section:
                case None:
                    if line.startswith("osu file format v"):
                        map.file_format = int(line.split("osu file format v")[1])
                        continue

                case "General":
                    kw, val = [s.strip() for s in line.split(":")]
                    match kw:
                        case "AudioFilename":
                            map.audio_filename = val
                            continue
                        case "AudioLeadIn":
                            map.audio_lead_in = int(val)
                            continue
                        case "PreviewTime":
                            map.preview_time = int(val)
                            continue
                        case "Countdown":
                            map.countdown = int(val)
                            continue
                        case "SampleSet":
                            map.sample_set = val
                            continue
                        case "StackLeniency":
                            map.stack_leniency = float(val)
                            continue
                        case "LetterboxInBreaks":
                            map.letterbox_in_breaks = int(val) == 1
                            continue
                        case "UseSkinSprites":
                            map.use_skin_sprites = int(val) == 1
                            continue
                        case "OverlayPosition":
                            map.overlay_position = val
                            continue
                        case "SkinPreference":
                            map.skin_preference = val
                            continue
                        case "EpilepsyWarning":
                            map.epilepsy_warning = int(val) == 1
                            continue
                        case "CountdownOffset":
                            map.countdown_offset = int(val)
                            continue
                        case "WidescreenStoryboard":
                            map.widescreen_storyboard = int(val) == 1
                            continue
                        case "SamplesMatchPlaybackRate":
                            map.samples_match_playback_rate = int(val) == 1
                            continue
                        case "Mode":
                            is_standard_mode_map = int(val) == 0
                            if not is_standard_mode_map:
                                break
                        case "AlwaysShowPlayfield" | "StoryFireInFront" | "AudioHash" | "EditorBookmarks" | "EditorDistanceSpacing":
                            continue  # Deprecated / Useless here
                        case _:
                            print(f"Unknown keyword in section {section}: {kw}")
                            continue
                
                case "Editor":
                    continue  # Don't care about editor data >:)

                case "Metadata":
                    kw, val = line.split(":")[0].strip(), ":".join(line.split(":")[1:]).strip()
                    match kw:
                        case "Title":
                            map.title = val
                            continue
                        case "TitleUnicode":
                            map.title_unicode = val
                            continue
                        case "Artist":
                            map.artist = val
                            continue
                        case "ArtistUnicode":
                            map.artist_unicode = val
                            continue
                        case "Creator":
                            map.creator = val
                            continue
                        case "Version":
                            map.diff_name = val
                            continue
                        case "Source":
                            map.source = val
                            continue
                        case "Tags":
                            map.tags = val
                            continue
                        case "BeatmapID":
                            map.id = int(val)
                            continue
                        case "BeatmapSetID":
                            map.set_id = int(val)
                            continue
                        case _:
                            print(f"Unknown keyword in section {section}: {kw}")
                            continue

                case "Difficulty":
                    kw, val = [s.strip() for s in line.split(":")]
                    match kw:
                        case "HPDrainRate":
                            map.hp_drain_rate = float(val)
                            continue
                        case "CircleSize":
                            map.circle_size = float(val)
                            continue
                        case "OverallDifficulty":
                            map.overall_difficulty = float(val)
                            continue
                        case "ApproachRate":
                            map.approach_rate = float(val)
                            continue
                        case "SliderMultiplier":
                            map.slider_multiplier = float(val)
                            continue
                        case "SliderTickRate":
                            map.slider_tick_rate = float(val)
                            continue
                
                case "Events":
                    event = Event(map_id=map.id)

                    data = line.split(",")
                    
                    event.event_type_id = EVENT_TYPE_MAP.get(data[0], 3)  # Map int/string first param into int
                    try:
                        event.time_start = int(data[1])
                    except:  # Don't save storyboard events such as "Sprite,Foreground,Centre,"neimuu\Mythol.png",320,240"
                        continue

                    # Data structure differs between event types
                    match event.event_type_id:
                        case 0 | 1:
                            event.file_name = data[2]
                            # Offsets are 0 by default when not written, only for these event types
                            event.x_offset = data[3] if len(data) >= 4 else 0
                            event.y_offset = data[4] if len(data) >= 5 else 0
                        case 2:
                            event.time_end = data[2]
                        case 3:
                            event.event_param = ",".join(data[2:])

                    conn.insert_event(event)

                case "TimingPoints":
                    data = line.split(",")

                    tp = Timing_point(
                        map_id=map.id,
                        time=float(data[0]),
                        beat_length=float(data[1])
                    )
                    
                    if len(data) >= 3:
                        tp.meter=int(data[2])
                    if len(data) >= 4:
                        tp.sample_set=int(data[3])
                    if len(data) >= 5:
                        tp.sample_index=int(data[4])
                    if len(data) >= 6:
                        tp.volume = int(data[5])
                    if len(data) >= 7:
                        tp.uninherited = int(data[6]) == 1
                    if len(data) >= 8:
                        tp.kiai_time = int(data[7]) == 1

                    map_timing_points.append(tp)
                    conn.insert_timing_point(tp)

                case "Colours":
                    continue  # Colours are cool and all but they're already easy enough to set, too lazy to have them here x)

                case "HitObjects":
                    data = line.split(",")

                    cur_map_obj_nr += 1

                    ho = Hit_obj(
                        map_id=map.id,
                        x=int(data[0]),
                        y=int(data[1]),
                        time=int(data[2]),
                        obj_type_id=int(data[3]) % 16,  # Don't care about the colour skip bits
                        hit_sound=int(data[4])
                    )
                    hod: Optional[Hit_obj_det] = None
                    map_last_ho_time = ho.time

                    if ":" in data[-1]:  # Ensure the last value corresponds to the right type (i.e. it is written) before overriding the default value
                        ho.hit_sample = data[-1]

                    ho.id = conn.insert_hit_obj(ho)

                    if ho.obj_type_id in {2, 6, 8, 12}:  # Object is of type slider or spinner, so it is going to have an entry in hit_obj_det table
                        # Update the entry to add the corresponding id in table hit_obj already
                        ho.hit_obj_det_id = ho.id
                        conn.update("hit_obj", {"hit_obj_det_id": ho.hit_obj_det_id}, ho.id)

                        # Create the detail object and insert it as well
                        hod = Hit_obj_det(id=ho.hit_obj_det_id)
                        match ho.obj_type_id:
                            case 2 | 6:  # Slider
                                hod.curve_data = data[5] if len(data) >= 6 else None
                                hod.slides = int(data[6]) if len(data) >= 7 else None
                                hod.length = float(data[7]) if len(data) >= 8 else None
                                hod.edge_sounds = data[8] if len(data) >= 9 else None
                                hod.edge_sets = data[9] if len(data) >= 10 else None
                                hod.time_end = ho.time + (hod.length / (map.slider_multiplier * 100 * (-100/get_cur_neg_inv_svm(ho.time, map_timing_points))) * get_cur_bl(ho.time, map_timing_points))

                            case 8 | 12:  # Spinner
                                hod.time_end = int(data[5]) if len(data) >= 6 else None

                        conn.insert_hit_obj_det(hod)

                    if ho.obj_type_id in {5, 6, 12} or last_pattern_id is None:  # Object is the start of a new combo
                        # Calc stats for last pattern
                        if last_pattern_id is not None:
                            # Compute end time and coordinate of the pattern given the last object
                            pat_first_ho = cur_pattern_ho_extn[0][0]
                            pat_last_ho = cur_pattern_ho_extn[-1][0]
                            pat_coos_end = (pat_last_ho.x, pat_last_ho.y)
                            pat_time_end = pat_last_ho.time
                            if pat_last_ho.obj_type_id in {2, 6, 8, 12}:
                                last_hod = cur_pattern_ho_extn[-1][1]
                                # End time of pattern is end of slider / spinner if last ho is of these types
                                pat_time_end = last_hod.time_end
                                # End coos would be end of slider as well if it is of that type
                                if pat_last_ho.obj_type_id in {2, 6}:
                                    pat_coos_end = get_last_curve_point(pat_last_ho, last_hod)

                            # Let's define spacing by "Amount of osu!pixels between the end of an HO and the start of the next, divided by the time between those two events"
                            pattern_size = len(cur_pattern_ho_extn)
                            spacing_sum: Optional[float] = 0. if pattern_size > 1 else None
                            for i in range(pattern_size - 1):
                                l_ho = cur_pattern_ho_extn[i][0]
                                l_ho_next = cur_pattern_ho_extn[i + 1][0]
                                l_ho_time_end: int = l_ho.time
                                l_ho_coos_end: Tuple[float, float] = (l_ho.x, l_ho.y)
                                if l_ho.obj_type_id in {2, 6, 8, 12}:  # End time is different for spinners and sliders
                                    l_hod = cur_pattern_ho_extn[i][1]
                                    l_ho_time_end = l_hod.time_end
                                    if l_ho.obj_type_id in {2, 6}:  # End coos are different for sliders only
                                        l_ho_coos_end = get_last_curve_point(l_ho, l_hod)
                                try:
                                    spacing_sum += ((l_ho_next.x - l_ho_coos_end[0])**2 + (l_ho_next.y - l_ho_coos_end[1])**2)**(1/2) / (l_ho_next.time - l_ho_time_end)
                                except ZeroDivisionError:
                                    # If end of ho is exactly the same time as next ho, set spacing back to None to ignore it for this pattern
                                    spacing_sum = None
                                    break
                            
                            # Aggregate final pattern stats
                            pattern.duration                 = pat_time_end - pat_first_ho.time
                            pattern.size                     = pattern_size
                            pattern.avg_spacing              = spacing_sum / pattern.size if spacing_sum is not None else None
                            pattern.x_start, pattern.y_start = pat_first_ho.x, pat_first_ho.y
                            pattern.x_end, pattern.y_end     = pat_coos_end
                            pattern.time_start               = pat_first_ho.time

                            # Finally update them in db
                            conn.update(
                                "pattern",
                                {
                                    "duration":    pattern.duration,
                                    "size":        pattern.size,
                                    "avg_spacing": pattern.avg_spacing,
                                    "x_start":     pattern.x_start,
                                    "y_start":     pattern.y_start,
                                    "x_end":       pattern.x_end,
                                    "y_end":       pattern.y_end,
                                    "time_start":  pattern.time_start
                                },
                                id=last_pattern_id
                            )

                        # Update pattern-related variables to prepare for next combo (which starts with the current hit object)
                        pattern = Pattern(map_id=map.id)
                        pattern.id = conn.insert_pattern(pattern)
                        last_pattern_id = pattern.id
                        cur_pattern_ho_extn = []

                    # Update pattern with current ho and update table hit_obj
                    ho.pattern_id = pattern.id
                    ho.map_obj_nr = cur_map_obj_nr
                    cur_pattern_ho_extn.append((ho, hod))
                    conn.update("hit_obj", {"pattern_id": ho.pattern_id, "map_obj_nr": ho.map_obj_nr, "pattern_obj_nr": len(cur_pattern_ho_extn)}, ho.id)

                case _:
                    print(f"Unknown section {section}")
                    continue
        
        # Add addicional map calc data
        if is_standard_mode_map:
            map.avg_bpm = calc_avg_bpm(map_timing_points, map_last_ho_time)
            if map.star_rating is None:
                try:  # Sr calc may fail for older formats :/
                    with warnings.catch_warnings():  # Suppress warning (same for pretty much every map).
                        warnings.filterwarnings(
                            "ignore",
                            message=".*first timing point after current hit object.*"
                        )
                        map.star_rating = calculateStarRating(filepath=os.path.join(MAP_LIST_PATH, map.file_name))["nomod"]
                except UnicodeEncodeError:
                    print(f"Failed to compute star rating because of a non-unicode character in the map's file path: {''.join(filter(str.isascii, file))}")
                except Exception as e:
                    print(f"Failed to compute star rating: {e}")

            conn.update("beatmap", {"star_rating": map.star_rating, "avg_bpm": map.avg_bpm}, id=map.id)

        if map_cnt % 100 == 0:
            conn.commit()  # Commit every 100 .osu files
        
    conn.commit()

    print("Finished processing .osu files.")
    conn.close()


def add_calc_beatmap_data():
    conn = Db_conn()

    print("Adding beatmap calc data...")
    maps = conn.select("beatmap", limit=None)
    map_cnt = len(maps)
    for map_i, map_row in enumerate(maps):
        map = Beatmap(**map_row)
        osu_file_path = os.path.join(MAP_LIST_PATH, map.file_name)
        
        print(f"Computing calc data for map {map_i}/{map_cnt}: {''.join(filter(str.isascii, map.file_name))}...")

        # Star Rating
        if map.star_rating is None:
            try:  # Sr calc may fail for older formats :/
                with warnings.catch_warnings():  # Suppress warning (same for pretty much every map).
                    warnings.filterwarnings(
                        "ignore",
                        message=".*first timing point after current hit object.*"
                    )
                    map.star_rating = calculateStarRating(filepath=osu_file_path)["nomod"]
            except:
                pass

        # Average BPM
        if map.avg_bpm is None:
            timing_points = [Timing_point(**tp_row) for tp_row in conn.select("timing_point", dict={"map_id": map.id}, order_by=["time asc"], limit=None)]
            last_ho_time = Hit_obj(**conn.select("hit_obj", dict={"map_id": map.id}, order_by=["time desc"], limit=1)[0]).time
            map.avg_bpm = calc_avg_bpm(timing_points, last_ho_time)

        print({"star_rating": map.star_rating, "avg_bpm": map.avg_bpm})

        conn.update("beatmap", {"star_rating": map.star_rating, "avg_bpm": map.avg_bpm}, map.id)

        if map_i % 100 == 0:
            conn.commit()
        
    conn.commit()
    
    print("Finished adding beatmap calc data.")


if __name__ == "__main__":
    init_schema()
    add_beatmapsets_json_data()
    add_osu_files_data()
