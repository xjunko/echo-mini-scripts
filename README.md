# normalize-album-art

a Rust CLI that scans a music folder and normalizes embedded album art to square JPEG images.

- default output size is `500x500`.
- if a track has missing/invalid art, it tries to use a nearby image in the same folder (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`).

  
**[[latest download]](https://github.com/xjunko/echo-mini-scripts/releases/latest)**

## build

```bash
cargo build --release
```

## usage

run with defaults (`500x500`):

```bash
cargo run --release -- /path/to/music
```

set a custom target size:

```bash
cargo run --release -- /path/to/music --size 600
```

you can also run the compiled binary directly:

```bash
./target/release/normalize-album-art /path/to/music --size 500
```

## supported audio file extensions

- `mp3`
- `flac`
- `ogg`
- `m4a`
- `opus`
- `wav`
