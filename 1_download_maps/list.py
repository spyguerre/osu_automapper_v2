from playwright.sync_api import sync_playwright
import json
import os


# Add your osu_session cookie in the file 1_download_maps/osu_session, since it is required to perform any search on the ppy website.
OSU_SESSION = open(os.path.join("1_download_maps", "osu_session"), "r").read().strip()


def handle_response(response, all_beatmapsets):
    if "/beatmapsets/search" in response.url:
        try:
            data = response.json()
            if "beatmapsets" in data:
                all_beatmapsets.extend([
                    {
                        "id": map_set["id"],
                        "artist": map_set["artist"],
                        "title": map_set["title"],
                        "creator": map_set["creator"],
                        "play_count": map_set["play_count"],
                    } for map_set in data["beatmapsets"]])
        except:
            pass


def collect_beatmapsets():
    all_beatmapsets = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies([
            {
                "name": "osu_session",
                "value": OSU_SESSION,
                "domain": ".ppy.sh",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            }
        ])
        page = context.new_page()

        page.on("response", lambda resp: handle_response(resp, all_beatmapsets))

        page.goto("https://osu.ppy.sh/beatmapsets?m=0&s=ranked&sort=plays_desc")

        print("Scroll the page for a few seconds...")
        
        beatmapsets = []
        # Let infinite scroll trigger multiple requests
        while len(beatmapsets) < 4999:  # Beatmap sets are loaded 50 at a time, so 100 scrolls should get you about 5000 beatmaps :)
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(1000)
            
            # Remove duplicate beatmaps just in case
            unique = {}
            for bm in all_beatmapsets:
                unique[bm["id"]] = bm

            beatmapsets = list(unique.values())

        browser.close()

    print("Raw collected:", len(all_beatmapsets))

    

    print("Unique beatmapsets:", len(beatmapsets))

    return beatmapsets


if __name__ == "__main__":
    # Fetch info on ppy website using playwright
    beatmapsets = collect_beatmapsets()

    # Save to JSON
    out_path = os.path.join("1_download_maps", "beatmapsets.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(beatmapsets, f, ensure_ascii=False, indent=2)
    print(f"Saved beatmapset list to {out_path}")
