import subprocess
import os


VIDEO_URL: str = "https://www.youtube.com/watch?v=k5B_9sJ1FDI"
OUT_PATH:  str = os.path.join("record_taps")

if __name__ == "__main__":
    # Clean old .mp3 or .webm files
    for file in os.listdir(OUT_PATH):
        if file.endswith(".mp3") or file.endswith(".webm"):
            os.remove(os.path.join(OUT_PATH, file))
    
    # Ensure yt-dlp is present and up to date
    subprocess.run(["pip", "install", "yt-dlp", "-U"])
    
    # Download audio from youtube link
    subprocess.run(["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "mp3", "-P", OUT_PATH, VIDEO_URL])
