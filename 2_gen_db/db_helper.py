import sqlite3
from osu_dataclasses import *
from typing import Dict, Any, Optional, List
import os


class Db_conn():
    def __init__(self):
        self.DB_PATH = "osu_db.db"
        self.conn = sqlite3.connect(self.DB_PATH)
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
