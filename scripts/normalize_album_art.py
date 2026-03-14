import argparse
import gzip
import json
import sys
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import tqdm
from mutagen import flac
from mutagen import id3
from PIL import Image

AUDIO_HEADERS: dict[str, Callable[[bytes], bool]] = {
    "WAV": lambda h: h.startswith(b"RIFF") and h[8:12] == b"WAVE",
    "MP3": lambda h: h.startswith(b"ID3") or h[:2] == b"\xff\xfb",
    "FLAC": lambda h: h.startswith(b"fLaC"),
    "OGG": lambda h: h.startswith(b"OggS"),
    "M4A_AAC": lambda h: b"ftyp" in h,
    "AIFF": lambda h: h.startswith(b"FORM") and h[8:12] == b"AIFF",
}


def resize_image(data: bytes, size: int = 500) -> tuple[bytes | None, bool]:
    img = Image.open(BytesIO(data))
    if img.size[0] == size and img.size[1] == size:
        return None, False

    img = img.convert("RGB")
    img = img.resize((size, size))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), True


def get_from_cache(path: str) -> tuple[str, bool] | None:
    return _cache.get(path)


def add_to_cache(path: str, fmt: str, valid: bool) -> None:
    _cache[path] = (fmt, valid)


def save_cache(path: Path) -> None:
    with gzip.open(path, "wt") as f:
        json.dump(_cache, f, separators=(",", ":"))


def open_cache(path: Path) -> dict[str, tuple[str, bool]]:
    if path.exists():
        with gzip.open(path, "rt") as f:
            return json.load(f)
    else:
        print("Cache not found, checks will be slower.")
        return {}


_cache_file: Path = Path(".junko_cache")
_cache: dict[str, tuple[str, bool]] = open_cache(_cache_file)


class AudioFile:
    COVER_NAMES: list[str] = [
        "cover",
        "folder",
        "album",
        "art",
    ]

    COVER_FORMATS: list[str] = [
        ".jpg",
        ".jpeg",
        ".png",
    ]

    def __init__(self, root_dir: Path, file_path: Path):
        self.root = root_dir
        self.file = file_path
        self.fmt = ""

    def __str__(self) -> str:
        return f"{self.file.name} ({self.fmt})"

    def is_audio(self) -> bool:
        with self.file.open("rb") as f:
            header = f.read(16)

        for fmt, func in AUDIO_HEADERS.items():
            if func(header):
                self.fmt = fmt
                return True

        return False

    def find_cover(self, depth: int = 1) -> bytes | None:
        cur = self.file.parent

        for _ in range(depth + 1):
            for possible in cur.glob("*"):
                for name in AudioFile.COVER_NAMES:
                    if possible.is_file() and name in possible.name.lower():
                        return possible.read_bytes()

                for ext in AudioFile.COVER_FORMATS:
                    if possible.is_file() and possible.name.lower().endswith(ext):
                        return possible.read_bytes()

            if cur == cur.parent:
                break

            cur = cur.parent

        return None

    def embed_cover(self, data: bytes) -> bool:
        modified: bool = False

        if self.fmt == "FLAC":
            audio = flac.FLAC(self.file)

            if audio.pictures:
                for pic in audio.pictures:
                    resized_data, dirty = resize_image(pic.data)
                    if dirty:
                        pic.data = resized_data
                        modified = True
            else:
                pic = flac.Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                pic.data = data
                audio.add_picture(pic)
                modified = True

            if modified:
                audio.save()
            return modified
        elif self.fmt == "MP3":
            tags = id3.ID3(self.file)
            has_cover = any(frame.FrameID == "APIC" for frame in tags.values())
            if has_cover:
                for frame in tags.getall("APIC"):
                    resized_data, dirty = resize_image(frame.data)
                    if dirty:
                        frame.data = resized_data
                        modified = True
            else:
                tags.add(
                    id3.APIC(  # type: ignore
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=data,
                    ),
                )
                modified = True
            if modified:
                tags.save()
            return modified
        else:
            print("Unsupported format:", self.fmt)

        return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize album pictures in a directory, embedding them into audio files if necessary.",
    )
    parser.add_argument("root", type=str, help="Root directory to process")
    args = parser.parse_args(argv)

    root: Path = Path(args.root)
    if not root.exists():
        raise RuntimeError(f"Invalid Path: {root}")
    print(f"Root dir is: {root}")

    all_files = list(root.rglob("*"))
    print("Total files:", len(all_files))

    for cur_entry in tqdm.tqdm(all_files, desc="Processing files", unit="file"):
        if cur_entry.is_file():
            if (cur_audio := AudioFile(root, cur_entry)).is_audio() and (
                cover_data := cur_audio.find_cover()
            ):
                cur_audio.embed_cover(cover_data)

        else:
            pass

    save_cache(_cache_file)

    return 0


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
