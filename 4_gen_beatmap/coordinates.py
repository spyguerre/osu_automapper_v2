from typing import List
from osu_dataclasses import *
import json
import os
from db_helper import conn


def fill_next_coordinates(ho_list: Hit_obj_list, i_ho: int):
    r = conn.select_rd_patterns(start_prune_pct=99)
    print(len(r))
    # TODO WIP


if __name__ == "__main__":
    from timing import rec_to_ho_list, cast_ho_list
    recordings: List[dict] = json.load(open(os.path.join("3_record_taps", "recording.json"), "r"))
    
    rec0 = recordings[-1]
    ho_list = rec_to_ho_list(rec0)
    ho_list = cast_ho_list(ho_list)

    fill_next_coordinates([], 0)
