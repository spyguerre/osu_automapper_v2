import sqlite3
from osu_dataclasses import *
from typing import Dict, Any, Optional, List, Callable
import os


DB_PATH: str = "osu_db.db"


class Db_conn():
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self):
        try:
            self.conn.executescript(open(os.path.join("2_gen_db", "init_db.sql"), "r").read())
        except Exception as e:
            print(f"Error initializing schema: {e}")

    def insert_set(self, set: Beatmapset) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO beatmapset
                    (id, title, artist, creator, play_count)
                    VALUES (?, ?, ?, ?, ?);
                """,
                (set.id, set.title, set.artist, set.creator, set.play_count)
            )
            return cursor.lastrowid
        except Exception as e:
            print(e)
            return None
    
    def insert_map(self, map: Beatmap) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO beatmap
                    (id, set_id, star_rating, avg_bpm, file_name, file_format, title, title_unicode, artist, artist_unicode, creator, diff_name, source, tags, hp_drain_rate, circle_size, overall_difficulty, approach_rate, slider_multiplier, slider_tick_rate, audio_filename, audio_lead_in, preview_time, countdown, sample_set, stack_leniency, letterbox_in_breaks, use_skin_sprites, overlay_position, skin_preference, epilepsy_warning, countdown_offset, widescreen_storyboard, samples_match_playback_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (map.id, map.set_id, map.star_rating, map.avg_bpm, map.file_name, map.file_format, map.title, map.title_unicode, map.artist, map.artist_unicode, map.creator, map.diff_name, map.source, map.tags, map.hp_drain_rate, map.circle_size, map.overall_difficulty, map.approach_rate, map.slider_multiplier, map.slider_tick_rate, map.audio_filename, map.audio_lead_in, map.preview_time, map.countdown, map.sample_set, map.stack_leniency, map.letterbox_in_breaks, map.use_skin_sprites, map.overlay_position, map.skin_preference, map.epilepsy_warning, map.countdown_offset, map.widescreen_storyboard, map.samples_match_playback_rate)
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # In case a beatmap has a duplicate ID (how the hell could this happen too), try inserting again without the ID
            try:
                cursor = self.conn.execute(
                    """
                        INSERT INTO beatmap
                        (set_id, star_rating, avg_bpm, file_format, title, title_unicode, artist, artist_unicode, creator, diff_name, source, tags, hp_drain_rate, circle_size, overall_difficulty, approach_rate, slider_multiplier, slider_tick_rate, audio_filename, audio_lead_in, preview_time, countdown, sample_set, stack_leniency, letterbox_in_breaks, use_skin_sprites, overlay_position, skin_preference, epilepsy_warning, countdown_offset, widescreen_storyboard, samples_match_playback_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (map.set_id, map.star_rating, map.avg_bpm, map.file_format, map.title, map.title_unicode, map.artist, map.artist_unicode, map.creator, map.diff_name, map.source, map.tags, map.hp_drain_rate, map.circle_size, map.overall_difficulty, map.approach_rate, map.slider_multiplier, map.slider_tick_rate, map.audio_filename, map.audio_lead_in, map.preview_time, map.countdown, map.sample_set, map.stack_leniency, map.letterbox_in_breaks, map.use_skin_sprites, map.overlay_position, map.skin_preference, map.epilepsy_warning, map.countdown_offset, map.widescreen_storyboard, map.samples_match_playback_rate)
                )
                return cursor.lastrowid
            except Exception as e:
                print(e)
                return None
        except Exception as e:
            print(e)
            return None

    def insert_timing_point(self, tp: Timing_point) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO timing_point
                    (map_id, time, beat_length, meter, sample_set, sample_index, volume, uninherited, kiai_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (tp.map_id, tp.time, tp.beat_length, tp.meter, tp.sample_set, tp.sample_index, tp.volume, tp.uninherited, tp.kiai_time)
            )
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting timing point: {e}")
            return None

    def insert_event(self, event: Event) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO event
                    (map_id, event_type_id, time_start, file_name, x_offset, y_offset, time_end, event_params)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (event.map_id, event.event_type_id, event.time_start, event.file_name, event.x_offset, event.y_offset, event.time_end, event.event_params)
            )
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting event: {e}")
            return None

    def insert_pattern(self, pattern: Pattern) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO pattern
                    (map_id, duration, size, avg_spacing, x_start, y_start, x_end, y_end, time_start)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (pattern.map_id, pattern.duration, pattern.size, pattern.avg_spacing, pattern.x_start, pattern.y_start, pattern.x_end, pattern.y_end, pattern.time_start)
            )
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting pattern: {e}")
            return None
    
    def insert_hit_obj(self, ho: Hit_obj) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO hit_obj
                    (map_id, pattern_id, obj_type_id, hit_obj_det_id, x, y, time, hit_sound, hit_sample)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (ho.map_id, ho.pattern_id, ho.obj_type_id, ho.hit_obj_det_id, ho.x, ho.y, ho.time, ho.hit_sound, ho.hit_sample)
            )
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting Hit object: {e}")
            return None

    def insert_hit_obj_det(self, hod: Hit_obj_det) -> Optional[int]:
        try:
            cursor = self.conn.execute(
                """
                    INSERT INTO hit_obj_det
                    (id, curve_data, slides, length, edge_sounds, edge_sets, time_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (hod.id, hod.curve_data, hod.slides, hod.length, hod.edge_sounds, hod.edge_sets, hod.time_end)
            )
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting Hit object detail: {e}")
            return None

    def get_beatmapset_id(self, map: Beatmap) -> Optional[int]:
        try:
            res: Optional[List[int]] = self.select(
                table="beatmapset",
                dict={"artist": f"'{map.artist.replace("'", "''")}'", "title": f"'{map.title.replace("'", "''")}'", "creator": f"'{map.creator}'"},
                cols=["id"],
                limit=1
            )
            if not res:  # If we can't find a corresponding beatmapset, it's probably because the creator changed their name
                # Fallback to searching without creator name, even if we end up picking the wrong beatmapset
                res = self.select(
                    table="beatmapset",
                    dict={"artist": f"'{map.artist.replace("'", "''")}'", "title": f"'{map.title.replace("'", "''")}'"},
                    cols=["id"],
                    limit=1
                )
            return res[0]["id"]

        except Exception as e:
            print(f"Error in fetching beatmapset id: {e}")
            return None

    def get_timing_points(self, map_id: int) -> Optional[List[Timing_point]]:
        try:
            r = self.select(
                table="timing_point",
                dict={"map_id": map_id},
                order_by=["time"],
                limit=None
            )
            return [Timing_point(**tp_dict) for tp_dict in r]
        except Exception as e:
            print("Error trying to fetch timing points: {e}")
            return None

    # Fetch a random selection of patterns that match the input criteria. Returns the random list of patterns as tuples such as (previous_pattern_last_ho, selected_pattern_ho_list).
    # Try to fetch "count" random rows corresponding to the input criteria up to "max_attempts" times,
    # while pruning candidate rows by a decreasing percentage starting at "start_prune_pct".
    def select_rd_patterns(
            self,
            count:           int                           = 10,
            sr_range:        Optional[Tuple[float, float]] = None,
            bpm_range:       Optional[Tuple[float, float]] = None,
            cs_range:        Optional[Tuple[float, float]] = None,
            spacing_range:   Optional[Tuple[float, float]] = None,
            start_prune_pct: int                           = 99,
            max_attempts:    int                           = 10
        ) -> Optional[List[Tuple[Hit_obj, Hit_obj_list]]]:
        query: Callable[[int], str] = lambda prune_pct : f"""
                    SELECT selpat.last_p_x_end, selpat.last_p_y_end, selpat.last_p_time_end, ho.*, hod.*
                    FROM hit_obj ho, (
                        SELECT filt.p_id
                              ,(SELECT lp.x_end FROM pattern lp WHERE lp.id = filt.last_p_id) AS last_p_x_end
                              ,(SELECT lp.y_end FROM pattern lp WHERE lp.id = filt.last_p_id) AS last_p_y_end
                              ,(SELECT COALESCE(lhod.time_end, lho.time) FROM pattern lp, hit_obj lho LEFT OUTER JOIN hit_obj_det lhod ON lho.hit_obj_det_id = lhod.id WHERE lp.id = filt.last_p_id AND lho.pattern_id = lp.id ORDER BY lho.time DESC) AS last_p_time_end
                        FROM (
                            SELECT p.id AS p_id, (
                                SELECT last_p.id
                                FROM pattern last_p
                                WHERE p.map_id = last_p.map_id
                                AND last_p.time_start < p.time_start
                                ORDER BY last_p.time_start DESC
                                LIMIT 1
                            ) AS last_p_id, abs(random()) AS r
                            FROM pattern p, beatmap m
                            WHERE m.id = p.map_id
                            {f"AND m.star_rating BETWEEN {sr_range[0]}      AND {sr_range[1]}     " if sr_range      is not None else ""}
                            {f"AND m.avg_bpm     BETWEEN {bpm_range[0]}     AND {bpm_range[1]}    " if bpm_range     is not None else ""}
                            {f"AND m.circle_size BETWEEN {cs_range[0]}      AND {cs_range[1]}     " if cs_range      is not None else ""}
                            {f"AND p.avg_spacing BETWEEN {spacing_range[0]} AND {spacing_range[1]}" if spacing_range is not None else ""}
                        ) filt
                        WHERE filt.r%100 >= {prune_pct}
                        ORDER BY filt.r
                        LIMIT {count if count is not None else 10}
                    ) selpat
                    LEFT OUTER JOIN hit_obj_det hod ON ho.hit_obj_det_id = hod.id
                    WHERE ho.pattern_id = selpat.p_id
                    ORDER BY selpat.p_id;
                """
        try:
            # Try to fetch "count" random rows corresponding to the input criteria up to "max_attempts" times,
            # while decreasing the random pruning percentage "cur_prn_pct" at each failed step
            cur_prn_pct: int = start_prune_pct
            len_found:   int = 0
            attempts:    int = 0
            cursor: Optional[sqlite3.Cursor] = None
            while len_found < count and attempts < max_attempts:
                cursor = self.conn.execute(query(cur_prn_pct))
                r = cursor.fetchall()

                cur_prn_pct = int(cur_prn_pct * 2./3.)
                len_found = len(r)
                attempts += 1

            # Format raw row data to a list of Tuple[last_ho, ho_info]
            ho_list: List[Tuple[Hit_obj, Ho_info]] = [
                (
                    # Model the end time and coordinates of the previous pattern as a Hit Circle
                    Hit_obj(obj_type_id=1, time=dict(row)["last_p_time_end"], x=dict(row)["last_p_x_end"], y=dict(row)["last_p_y_end"]),
                    # Retrieve ho_info list from rows
                    (
                        Hit_obj(**dict(list(dict(row).items())[3:14+1])),
                        Hit_obj_det(id=dict(row)["hit_obj_det_id"], **dict(list(dict(row).items())[15:21+1])) if dict(row)["hit_obj_det_id"] is not None else None
                    )
                ) for row in r
            ]

            # Group list individual Ho_info by patterns
            patterns: List[Tuple[Hit_obj, Hit_obj_list]] = []
            last_pat_id: Optional[int] = None
            for prev_pat_last_ho, ho_info in ho_list:
                ho, _ = ho_info
                cur_pat_id = ho.pattern_id
                if cur_pat_id != last_pat_id:
                    patterns.append((prev_pat_last_ho, []))
                    last_pat_id = cur_pat_id
                patterns[-1][1].append((ho_info))
            
            return patterns

        except Exception as e:
            print(f"Error in running query {query}: {e}")
            return None

    def select(self, table: str, dict: Optional[Dict[str, Any]] = None, cols: Optional[List[str]] = None, limit: Optional[int] = 200, order_by: Optional[List[str]] = None) -> Optional[List[Any]]:
        query = f"""
                    SELECT {", ".join(cols) if cols else "*"}
                    FROM {table}
                    {"WHERE " + " and ".join([col + " = " + str(val) for col, val in zip(dict.keys(), dict.values())]) if dict else ""}
                    {"ORDER BY " + ", ".join(order_by) if order_by else ""}
                    {"LIMIT " + str(limit) if limit else ""};
                """
        try:
            cursor = self.conn.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error in running query {query}: {e}")
            return None

    def update(self, table: str, dict: Dict[str, Any], id: int) -> Optional[int]:
        query = f"""
                    UPDATE {table}
                    SET {", ".join([col + " = " + str(val if val is not None else "null") for col, val in zip(dict.keys(), dict.values())])}
                    WHERE id = {id};
                """
        try:
            cursor = self.conn.execute(query)
            return cursor.lastrowid
        except Exception as e:
            print(f"Error in update query {query}: {e}")
            return None

    def commit(self):
        try:
            self.conn.commit()
        except Exception as e:
            print(e)
            self.conn.rollback()

    def close(self):
        self.conn.close()


conn = Db_conn()
