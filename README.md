# echo-mini-scripts
scrips that i used for my snowsky echo mini

## normalize album art
it basically ensures that all the music files has 500x500 album art.

this script scans a music folder, finds audio files, and normalizes embedded album art to a square jpeg (500x500).
if a file has no embedded cover, it tries to find a nearby image (like cover.jpg or folder.png) and embed it.

### usage:
```bash
python scripts/normalize_album_art.py /path/to/folder
```

### how to use:
1. make sure you have python 3.14+.
2. install deps:
	`pip install mutagen pillow tqdm`
3. run:
	`python normalize_album_art.py /path/to/music`
4. wait for it to finish scanning and writing updated tags.

### what it supports now:
- mp3 (id3 apic)
- flac
