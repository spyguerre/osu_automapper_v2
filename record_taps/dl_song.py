import subprocess
import os
import shutil


VIDEO_URL:    str = "https://www.youtube.com/watch?v=k5B_9sJ1FDI"
OUT_DIR:      str = os.path.join("record_taps")
LEAD_SILENCE: int = 10_000  # Leading silence for VLC player intialization, in ms

if __name__ == "__main__":
    # Clean up old .mp3 or .webm files
    for file in os.listdir(OUT_DIR):
        if file.endswith(".mp3") or file.endswith(".webm"):
            os.remove(os.path.join(OUT_DIR, file))
    
    # Ensure yt-dlp is present and up to date
    subprocess.run(["pip", "install", "yt-dlp", "-U"])
    
    # Download audio from youtube link
    subprocess.run(["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "mp3", "-P", OUT_DIR, VIDEO_URL])

    # Get downloaded video path
    out_fp: str | None = None
    dl_fp:  str | None = None
    for file in os.listdir(OUT_DIR):
        if file.endswith(".mp3"):
            out_fp = os.path.join(OUT_DIR, "[TapRec] " + file)
            dl_fp = os.path.join(OUT_DIR, file)
            break

    if dl_fp is None:
        raise RuntimeError("Failed to download video.")


    # Add 10 seconds of silence at the start of file; helps VLC synchronize get_time() properly
    subprocess.run(["ffmpeg", "-f", "lavfi", "-t", str(LEAD_SILENCE/1000),"-i", "anullsrc=r=44100:cl=stereo", 
                    "-i", dl_fp,
                    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
                    out_fp])
