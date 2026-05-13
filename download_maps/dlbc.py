from playwright.sync_api import sync_playwright
import json
import os
import time


beatmaps = json.load(open("download_maps/beatmaps.json", "r"))
os.makedirs("dataset", exist_ok=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    page = context.new_page()

    for i, bm in enumerate(beatmaps):
        set_id = bm["id"]

        if not os.path.exists(f"dataset/{set_id}.osz"):
            print(f"Downloading beatmap set {i}/{len(beatmaps)}:\nid      = {bm["id"]}\ntitle   = {bm["title"]}\nartist  = {bm["artist"]}\ncreator = {bm["creator"]}\n\n")
            
            try:
                page.goto(f"https://beatconnect.io/beatmapset/{set_id}", wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")

                main_btn = page.locator(
                    "button.base-button--primary:has-text('Download')"
                ).first

                # hover to reveal dropdown (if it exists)
                main_btn.hover()
                page.wait_for_timeout(500)

                no_video_option = page.locator(
                    "button.beatmapset-page__download-item:has-text('No Video')"
                )

                with page.expect_download() as dl:

                    # if dropdown exists and is visible → use it
                    if no_video_option.count() > 0:
                        no_video_option.first.click()
                    else:
                        # fallback: direct download click
                        main_btn.click()

                download = dl.value

                path = f"dataset/{set_id}.osz"
                download.save_as(path)

                time.sleep(1.5)

            except Exception as e:
                print("failed:", set_id, e)

    browser.close()
