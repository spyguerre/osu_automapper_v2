from playwright.sync_api import sync_playwright
import json
import os
import time


beatmapsets = json.load(open("download_maps/beatmapsets.json", "r"))
osu_session = open("download_maps/osu_session", "r").read().strip()

os.makedirs("dataset", exist_ok=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    context.add_cookies([
        {
            "name": "osu_session",
            "value": osu_session,
            "domain": ".ppy.sh",
            "path": "/",
            "httpOnly": True,
            "secure": True,
        }
    ])

    page = context.new_page()

    for i, bms in enumerate(beatmapsets):
        set_id = bms["id"]

        if not os.path.exists(f"dataset/{set_id}.osz"):
            print(f"Downloading beatmap set {i}/{len(beatmapsets)}:\nid      = {bms["id"]}\ntitle   = {bms["title"]}\nartist  = {bms["artist"]}\ncreator = {bms["creator"]}\n\n")
            try:
                page.goto(f"https://osu.ppy.sh/beatmapsets/{set_id}")

                # wait for page to fully load download buttons
                page.wait_for_load_state("networkidle")

                # prefer NO VIDEO button explicitly
                download_selector = (
                    f"a[href*='{set_id}/download?noVideo=1']"
                )

                # fallback if missing
                if page.query_selector(download_selector) is None:
                    download_selector = (
                        f"a[href*='{set_id}/download']"
                    )

                with page.expect_download() as dl:
                    page.click(download_selector)

                download = dl.value

                path = f"dataset/{set_id}.osz"
                download.save_as(path)

                time.sleep(1.5)  # important for rate limiting

            except Exception as e:
                print("failed:", set_id, e)

    browser.close()
