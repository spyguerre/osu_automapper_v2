from record import Recorder, LEAD_SILENCE
from osu_dataclasses import *
import os


CALIB_SONG_FP:    str = os.path.join("3_record_taps", "adofai_calibration.mp3")
CALIB_BPM:        int = 130    # BPM of the calibration song
CALIB_TIME_START: int = 10327  # In ms, calibrated start time of the timing point when you put the song in osu editor


def get_closest_beat_time(time: int) -> int:
    bl = 60_000 / CALIB_BPM  # Float Beat length
    closest_beat_index = round((time - (CALIB_TIME_START - LEAD_SILENCE)) / bl)  # Round to beat index
    return round((closest_beat_index) * bl + (CALIB_TIME_START - LEAD_SILENCE))  # Round to ms


def calibrate() -> str:
    print("You're going to calibrate your input offset with 3 consecutive recordings of the same audio, at different speeds. Get ready :)")

    try:
        recs: List[Recording] = []

        print("\nLoading with playback rate = 0.8 ...")
        recorder = Recorder(song_fp=CALIB_SONG_FP, rate=0.8)

        # Listen for inputs
        recs.append(recorder.record())

        print("\nLoading with playback rate = 1.0 ...")
        recorder = Recorder(song_fp=CALIB_SONG_FP, rate=1.0001)  # Rate 1.0 has a lot less latency; align on modified rate latency with .0001

        # Listen for inputs
        recs.append(recorder.record())

        print("\nLoading with playback rate = 1.2 ...")
        recorder = Recorder(song_fp=CALIB_SONG_FP, rate=1.2)

        # Listen for inputs
        recs.append(recorder.record())

    except KeyboardInterrupt:
        print("Canceled calibration.")
        exit()

    # Compute stats and prepare recap
    rec_offsets      = [sum([get_closest_beat_time(tap.time) - tap.time for tap in rec]) / len(rec) for rec in recs]
    rec_mean_abs_dev = [sum([abs(abs(rec_offsets[i]) - abs(get_closest_beat_time(tap.time) - tap.time)) for tap in rec]) / len(rec) for i, rec in enumerate(recs)]
    
    recap = f"""
Results offsets:
  Slow x 0.8:
    Average offset:      {rec_offsets[0]:.3f} ms
    Average consistency: {rec_mean_abs_dev[0]:.3f} ms
  Normal x 1.0:
    Average offset:      {rec_offsets[1]:.3f} ms
    Average consistency: {rec_mean_abs_dev[1]:.3f} ms
  Fast x 1.2:
    Average offset:      {rec_offsets[2]:.3f} ms
    Average consistency: {rec_mean_abs_dev[2]:.3f} ms

Recommended offset: {round(sum(rec_offsets)/len(rec_offsets))} ms
{
    "However, your tapping was not very consistent. You should probably try calibrating again and aim for an average consistency below ~20ms."
    if sum(rec_mean_abs_dev)/len(rec_mean_abs_dev) >= 20.
    else ""
}
"""
    print(recap)


if __name__ == "__main__":
    calibrate()
