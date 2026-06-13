import json
import os
from typing import List
from osu_dataclasses import *
from osu_helper import serialize_recordings


REC_JSON = os.path.join("3_record_taps", "recording.json")


def print_rec_data(recordings: List[Recording]) -> str:
    res = ""
    for i_rec, rec in enumerate(recordings):
        res += f"Recording n°{i_rec}:\n" \
               f"- Containing {len(rec)} tap events\n" \
               f"- From {f"{rec[0].time/1000}s" if rec else "-"} to {f"{rec[-1].time_end/1000}s" if rec else "-"}\n\n"        
    return res


if __name__ == "__main__":
    # Load recordings from file
    recordings: List[Recording] = [[Tap_event(**event) for event in rec] for rec in json.load(open(REC_JSON, "r"))]

    # Remove a recording
    i_to_remove: int = 0
    new_recordings = [rec for i_rec, rec in enumerate(recordings) if i_rec != i_to_remove]
    ser_new_recs = serialize_recordings(new_recordings)
    # Uncomment below to commit to file
    # json.dump(ser_new_recs, open(REC_JSON, "w"))

    # Print recordings data
    print(print_rec_data(recordings))
