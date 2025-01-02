import re
import sys
import json
from pathlib import Path

try:
    import stashapi.log as log
    from stashapi.tools import file_to_base64
except ModuleNotFoundError:
    print(
        "You need to install the stashapi module. (pip install stashapp-tools)",
        file=sys.stderr,
    )

image_file_extensions = [".jpg",".png"]
cover_pattern = r"(?:thumb|poster|cover)\.(?:jpg|png)"

def main():
    mode = sys.argv[1]
    fragment = json.loads(sys.stdin.read())

    data = None
    if mode == 'scene_fragment':
        data = scene_fragment(fragment)
    
    if data:
        print(json.dumps(data))
    else:
        print("null")


def scene_fragment(fragment):
    filepath = Path(fragment["files"][0]["path"])
    cover = find_cover(filepath)
    if not cover:
        return
    b64img = file_to_base64(cover)
    if not b64img:
        log.warning(f"Could not parse {filepath} to b64image")
        return
    
    return {"image":b64img}

def find_cover(filepath:Path):
    for file in filepath.parent.iterdir():
        if file == filepath:
            continue
        # return image with same name as scene file as long as it has an image suffix
        if file.suffix in image_file_extensions and file.stem == filepath.stem:
            return file
        # return image if it matches pattern
        if re.match(cover_pattern,file.name, re.IGNORECASE):
            return file


if __name__ == "__main__":
    main()