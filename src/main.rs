use std::collections::HashMap;
use std::io::Cursor;
use std::path::PathBuf;

use clap::Parser;
use image::ImageReader;
use image::imageops::FilterType;
use lofty::config::WriteOptions;
use lofty::file::TaggedFileExt;
use lofty::picture::{self, MimeType, Picture};
use lofty::probe::Probe;
use lofty::tag::TagExt;
use walkdir::WalkDir;

fn find_album_art_nearby(
    file_path: &std::path::Path,
) -> Option<std::path::PathBuf> {
    let parent_dir = file_path.parent()?;
    for entry in WalkDir::new(parent_dir).max_depth(1) {
        let entry = entry.ok()?;
        if entry.file_type().is_file() {
            let file_name = entry.file_name().to_string_lossy().to_lowercase();
            if file_name.ends_with(".jpg")
                || file_name.ends_with(".jpeg")
                || file_name.ends_with(".png")
                || file_name.ends_with(".webp")
                || file_name.ends_with(".bmp")
            {
                return Some(entry.path().to_path_buf());
            }
        }
    }
    None
}

#[derive(clap::Parser)]
struct Args {
    /// The root directory of the music files.
    path: String,

    /// The target size for album art (default: 500x500)
    #[clap(short, long, default_value = "500")]
    size: u32,
}

fn main() {
    let args = Args::parse();
    let root_dir = &args.path;
    let target_size = args.size;
    let mut art_cache: HashMap<PathBuf, Option<PathBuf>> = HashMap::new();

    for entry in WalkDir::new(root_dir) {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                panic!("{}", e);
            },
        };

        let metadata = match entry.metadata() {
            Ok(md) => md,
            Err(e) => {
                panic!("{}", e);
            },
        };

        let ext =
            entry.path().extension().and_then(|s| s.to_str()).unwrap_or("");

        if metadata.is_file()
            && matches!(ext, "mp3" | "flac" | "ogg" | "m4a" | "opus" | "wav")
            && let Ok(mut file) =
                Probe::open(entry.path()).expect("invalid path, somehow").read()
            && let Some(tag) = file.primary_tag_mut()
        {
            let mut new_pictures = Vec::new();
            let mut dirty = false;

            let parent = entry.path().parent().unwrap().to_path_buf();
            let nearby_art = art_cache
                .entry(parent.clone())
                .or_insert_with(|| find_album_art_nearby(entry.path()));

            tag.pictures().iter().for_each(|picture| {
                if let Ok(reader) = ImageReader::new(Cursor::new(picture.data()))
                    .with_guessed_format()
                {
                    let (width, height ) = reader.into_dimensions().expect("failed to get image dimensions");

                    if width == target_size && height == target_size && picture.mime_type() == Some(&MimeType::Jpeg) {
                        return;
                    }

                    if width != target_size && height != target_size {
                        let mut buf = Cursor::new(Vec::new());
                        if let Some(art_path) = &nearby_art {
                            let album_src_image = ImageReader::open(art_path)
                                .expect("failed to open nearby album art")
                                .decode()
                                .expect("failed to decode nearby album art");
                            let resized_img =
                                album_src_image.resize(target_size, target_size, FilterType::Lanczos3);
                            resized_img
                                .write_to(&mut buf, image::ImageFormat::Jpeg)
                                .expect("failed to write image into buffer");
                        } else if let Ok(img) = ImageReader::new(Cursor::new(picture.data()))
                            .with_guessed_format().expect("invalid image format").decode() {
                                let resized_img =
                                    img.resize(target_size, target_size, FilterType::Lanczos3);
                                resized_img
                                    .write_to(&mut buf, image::ImageFormat::Jpeg)
                                    .expect("failed to write image into buffer");
                        }
                        let new_picture = Picture::unchecked(buf.into_inner())
                            .pic_type(picture.pic_type())
                            .mime_type(picture::MimeType::Jpeg)
                            .build();
                        new_pictures.push(new_picture);
                        dirty = true;
                    }
                } else {
                    println!(
                        "Failed to decode existing album art for {}. Attempting to replace with nearby art.",
                        entry.path().display()
                    );
                    if let Some(art_path) = &nearby_art {
                        let new_image = ImageReader::open(art_path)
                            .expect("failed to open nearby album art")
                            .decode()
                            .expect("failed to decode nearby album art");
                        let resized_img =
                            new_image.resize(target_size, target_size, FilterType::Lanczos3);
                        let mut buf = Cursor::new(Vec::new());
                        resized_img
                            .write_to(&mut buf, image::ImageFormat::Jpeg)
                            .expect("failed to write image into buffer");

                        let new_picture = Picture::unchecked(buf.into_inner())
                            .pic_type(picture.pic_type())
                            .mime_type(picture::MimeType::Jpeg)
                            .build();
                        new_pictures.push(new_picture);
                        dirty = true;
                    }
                }
            });

            for (i, new_picture) in new_pictures.into_iter().enumerate() {
                tag.set_picture(i, new_picture);
            }

            if dirty {
                tag.save_to_path(entry.path(), WriteOptions::default())
                    .expect("failed to save tag");
            }
            println!("Processed: {}", entry.path().display());
        }
    }
}
