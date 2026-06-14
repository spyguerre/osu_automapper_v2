--------------------------
----- Init DB Schema -----
--------------------------

----- Init Tables -----

CREATE TABLE "code_event_type" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id")
);

INSERT INTO code_event_type (id, name) VALUES (1, "Video");
INSERT INTO code_event_type (id, name) VALUES (2, "Break");
INSERT INTO code_event_type (id, name) VALUES (3, "Storyboard");

CREATE TABLE "code_hit_obj_type" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id")
);

INSERT INTO code_hit_obj_type (id, name) VALUES (1, "Hit Circle");
INSERT INTO code_hit_obj_type (id, name) VALUES (2, "Slider");
INSERT INTO code_hit_obj_type (id, name) VALUES (5, "Hit Circle With New Combo");
INSERT INTO code_hit_obj_type (id, name) VALUES (6, "Slider With New Combo");
INSERT INTO code_hit_obj_type (id, name) VALUES (8, "Spinner");
INSERT INTO code_hit_obj_type (id, name) VALUES (12, "Spinner With New Combo");

CREATE TABLE "event" (
	"id"	INTEGER NOT NULL,
	"map_id"	INTEGER NOT NULL,
	"event_type_id"	INTEGER NOT NULL,
	"time_start" INTEGER NOT NULL,
	"file_name"	TEXT,
	"x_offset"	INTEGER,
	"y_offset"	INTEGER,
	"time_end"	INTEGER,
	"event_params"	TEXT,
	PRIMARY KEY("id"),
	FOREIGN KEY("event_type_id") REFERENCES "",
	FOREIGN KEY("map_id") REFERENCES "map"("id")
);

CREATE TABLE "hit_obj" (
	"id"	INTEGER NOT NULL,
	"map_id"	INTEGER NOT NULL,
	"pattern_id"	INTEGER,
	"obj_type_id"	INTEGER NOT NULL,
	"hit_obj_det_id"	INTEGER,
	"x"	INTEGER NOT NULL,
	"y"	INTEGER NOT NULL,
	"time"	INTEGER NOT NULL,
	"hit_sound"  INTEGER NOT NULL,
	"hit_sample"   TEXT,
	"map_obj_nr"	INTEGER,
	"pattern_obj_nr"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("map_id") REFERENCES "map"("id"),
	FOREIGN KEY("obj_type_id") REFERENCES "code_hit_obj_type"("id"),
	FOREIGN KEY("pattern_id") REFERENCES "pattern"("id")
);

CREATE TABLE "hit_obj_det" (
	"id"	INTEGER NOT NULL,
	"curve_data"	TEXT,
	"slides"	INTEGER,
	"length"	NUMERIC,
	"edge_sounds"	TEXT,
	"edge_sets"	TEXT,
	"time_end"	INTEGER,
	PRIMARY KEY("id"),
	FOREIGN KEY("id") REFERENCES "hit_obj"("id")
);

CREATE TABLE "beatmap" (
	"id"	INTEGER NOT NULL,
	"set_id"	INTEGER NOT NULL,
	"star_rating"	NUMERIC,
	"avg_bpm"	NUMERIC,
	"file_name"   TEXT,
	"file_format"	INTEGER NOT NULL,
	"title"	TEXT NOT NULL,
	"title_unicode"	TEXT NOT NULL,
	"artist"	TEXT NOT NULL,
	"artist_unicode"	TEXT NOT NULL,
	"creator"	TEXT NOT NULL,
	"diff_name"	TEXT NOT NULL,
	"source"	TEXT,
	"tags"	TEXT,
	"hp_drain_rate"	NUMERIC NOT NULL,
	"circle_size"	NUMERIC NOT NULL,
	"overall_difficulty"	NUMERIC NOT NULL,
	"approach_rate"	NUMERIC NOT NULL,
	"slider_multiplier"	NUMERIC NOT NULL,
	"slider_tick_rate"	NUMERIC NOT NULL,
	"audio_filename"	TEXT NOT NULL,
	"audio_lead_in"	INTEGER NOT NULL,
	"preview_time"	INTEGER NOT NULL,
	"countdown"	INTEGER NOT NULL,
	"sample_set"	TEXT NOT NULL,
	"stack_leniency"	NUMERIC NOT NULL,
	"letterbox_in_breaks"	INTEGER NOT NULL COLLATE BINARY,
	"use_skin_sprites"	INTEGER NOT NULL COLLATE BINARY,
	"overlay_position"	TEXT NOT NULL,
	"skin_preference"	TEXT,
	"epilepsy_warning"	INTEGER NOT NULL COLLATE BINARY,
	"countdown_offset"	INTEGER NOT NULL,
	"widescreen_storyboard"	INTEGER NOT NULL COLLATE BINARY,
	"samples_match_playback_rate"	INTEGER NOT NULL COLLATE BINARY,
	PRIMARY KEY("id"),
	FOREIGN KEY("set_id") REFERENCES "set"("id")
);

CREATE TABLE "pattern" (
	"id"	INTEGER NOT NULL,
	"map_id"	INTEGER NOT NULL,
	"duration"	NUMERIC,
	"size"	INTEGER,
	"avg_spacing"	NUMERIC,
	"x_start"	INTEGER,
	"y_start"	INTEGER,
	"x_end"	INTEGER,
	"y_end"	INTEGER,
	"time_start"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("map_id") REFERENCES "map"("id")
);

CREATE TABLE "beatmapset" (
	"id"	INTEGER NOT NULL,
	"title"	TEXT NOT NULL,
	"artist"	TEXT NOT NULL,
	"creator"	TEXT NOT NULL,
	"play_count"	INTEGER NOT NULL,
	PRIMARY KEY("id")
);

CREATE TABLE "timing_point" (
	"id"	INTEGER NOT NULL,
	"map_id"	INTEGER NOT NULL,
	"time"	NUMERIC NOT NULL,
	"beat_length"	NUMERIC NOT NULL,
	"meter"	INTEGER NOT NULL,
	"sample_set"	TEXT NOT NULL,
	"sample_index"	INTEGER NOT NULL,
	"volume"	INTEGER NOT NULL,
	"uninherited"	INTEGER NOT NULL COLLATE BINARY,
	"kiai_time"	INTEGER NOT NULL COLLATE BINARY,
	PRIMARY KEY("id"),
	FOREIGN KEY("map_id") REFERENCES "map"("id")
);


----- Define Indexes -----

-- Indexes for table beatmap

CREATE INDEX "beatmap_avg_bpm_ind" ON "beatmap" (
	"avg_bpm"
);

CREATE INDEX "beatmap_circle_size_ind" ON "beatmap" (
	"circle_size"
);

CREATE INDEX "beatmap_id_ind" ON "beatmap" (
	"id"
);

CREATE INDEX "beatmap_set_id_ind" ON "beatmap" (
	"set_id"
);

CREATE INDEX "beatmap_start_rating_ind" ON "beatmap" (
	"star_rating"
);


-- Indexes for table beatmapset

CREATE INDEX "beatmapset_id_ind" ON "beatmapset" (
	"id"
);

CREATE INDEX "beatmapset_play_count_ind" ON "beatmapset" (
	"play_count"
);


-- Indexes for table event

CREATE INDEX "event_id_ind" ON "event" (
	"id"
);

CREATE INDEX "event_map_id_ind" ON "event" (
	"map_id"
);


-- Indexes for table hit_obj_det

CREATE INDEX "hit_obj_det_id_ind" ON "hit_obj_det" (
	"id"
);

CREATE INDEX "hit_obj_det_time_end_ind" ON "hit_obj_det" (
	"time_end"
);


-- Indexes for table hit_obj

CREATE INDEX "hit_obj_id_ind" ON "hit_obj" (
	"id"
);

CREATE INDEX "hit_obj_map_id_ind" ON "hit_obj" (
	"map_id"
);

CREATE INDEX "hit_obj_pattern_id_ind" ON "hit_obj" (
	"pattern_id"
);

CREATE INDEX "hit_obj_time_ind" ON "hit_obj" (
	"time"
);

CREATE INDEX "hit_obj_x_y_ind" ON "hit_obj" (
	"x",
	"y"
);


-- Indexes for table pattern

CREATE INDEX "pattern_avg_spacing_ind" ON "pattern" (
	"avg_spacing"
);

CREATE INDEX "pattern_id_ind" ON "pattern" (
	"id"
);

CREATE INDEX "pattern_map_id_ind" ON "pattern" (
	"map_id"
);

CREATE INDEX "pattern_time_start_ind" ON "pattern" (
	"time_start"
);

CREATE INDEX "pattern_x_y_start_ind" ON "pattern" (
	"x_start",
	"y_start"
);

CREATE INDEX "pattern_x_y_end_ind" ON "pattern" (
	"x_end",
	"y_end"
);


-- Indexes for table timing_point

CREATE INDEX "timing_point_id_ind" ON "timing_point" (
	"id"
);

CREATE INDEX "timing_point_map_id_ind" ON "timing_point" (
	"map_id"
);
