import os
import zipfile
import shutil


os.makedirs("dataset/maps/", exist_ok=True)


for file in os.listdir("dataset"):
    set_id = file.split(".")[0]

    if file == "maps" or str(file) < "42110":
        continue
    
    print(f"Extracting: {file}")
    
    zf = zipfile.ZipFile(f"dataset/{file}")
    zf.extractall(path=f"dataset/maps/{set_id}/")

    for osu_file in os.listdir(f"dataset/maps/{set_id}/"):
        if osu_file.split(".")[-1] == "osu":
            try:
                shutil.move(f"dataset/maps/{set_id}/{osu_file}", f"dataset/maps/")
            except shutil.Error:
                pass
    shutil.rmtree(f"dataset/maps/{set_id}/")
