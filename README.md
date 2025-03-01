# Google Photos / Takeout Import Script

This Python script is designed to help organize and manage photos and videos from **Google Photos** or **Google Takeout** exports, focusing on importing media to iCloud, managing albums in Apple Photos, and enabling HDR live photo imports.

## Features

- **Album Management**: Checks and creates albums in Apple Photos.
- **iCloud Integration**: Imports new photos and videos to iCloud, and checks if they already exist.
- **Live Photo Support**: Automatically imports HDR live photo pairs (image + video) to iCloud.
- **Google Photos Takeout Support**: Specifically developed to handle files exported from Google Photos or Google Takeout.

## Requirements

- macOS with **AppleScript** support.
- Python 3.
- `exiftool` (install via Homebrew: `brew install exiftool`).

## Usage

```bash
python iCloudImport.py <folder_path> [--check-library]
```

- `<folder_path>`: Path to the folder containing photos and videos to process (usually from Google Photos or Google Takeout).
- `--check-library`: Optional flag to check if photos are already in iCloud before processing. This adds duplicated photos to an album for easy deletion and adds photos to a favorite album.

Example:

```bash
python iCloudImport.py /path/to/your/takeout/folder --check-library
```

### What It Does:
- Checks if albums exist in Apple Photos, creating them if necessary.
- Imports new photos/videos to iCloud and organizes them.
- Adds HDR live photos (image + video) to iCloud as a pair.

