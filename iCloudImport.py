import os
import subprocess
import pathlib
import uuid
import threading
import glob
import objc
import AVFoundation
from Foundation import NSURL
import sys


def album_exists(album_name):
    apple_script = f'''
    tell application "Photos"
        set albumExists to false
        set allAlbums to albums

        repeat with anAlbum in allAlbums
            if name of anAlbum is "{album_name}" then
                set albumExists to true
                exit repeat
            end if
        end repeat

        if albumExists is false then
            set newAlbum to make new album named "{album_name}"
        else
            set newAlbum to album "{album_name}"
        end if

        return newAlbum
    end tell
    '''
    result = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def add_photo_to_album(filename, album_name):
    name_without_extension, extension = os.path.splitext(filename)
    album = album_exists(album_name)  # Ensure album exists or is created
    apple_script = f'''
    tell application "Photos"
        set foundItems to every media item whose filename contains "{name_without_extension}"
        add foundItems to album named "{album_name}"
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script], check=True)

def photo_exists_in_icloud(filename):
    name_without_extension, extension = os.path.splitext(filename)
    apple_script = f'''
    tell application "Photos"
        set foundItems to every media item whose filename contains "{name_without_extension}"
        if (count of foundItems) > 0 then
            set isLiked to false
            repeat with anItem in foundItems
                -- Überprüfe, ob das Bild geliked wurde
                if favorite of anItem is true then
                    set isLiked to true
                end if
            end repeat
            return "found, liked: " & isLiked
        else
            return "not found"
        end if
    end tell
    '''
    result = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
    output = result.stdout.strip()
    print(f"File {name_without_extension}: {output}") 
    return output # "not found", "found, liked: false", "found, liked: true"

def add_photo_to_icloud(photo_path):
    print(f"Importing {photo_path} to iCloud")
    script = f'''
    tell application "Photos"
        import {{POSIX file "{photo_path}" as alias}} into album "Imported" skip check duplicates true
    end tell'''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        os.remove(photo_path)
        return True
    except subprocess.CalledProcessError:
        return False

def add_live_photo_to_icloud(photo_path1, photo_path2):
    print(f"Importing live photo pair: {photo_path1}, {photo_path2}")
    script = f'''
    tell application "Photos"
        import {{POSIX file "{photo_path1}" as alias, POSIX file "{photo_path2}" as alias}} into album "Imported" skip check duplicates true
    end tell'''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        os.remove(photo_path1)
        os.remove(photo_path2)
        return True
    except subprocess.CalledProcessError:
        return False

def add_content_identifier_to_mp4(filepath, asset_id):
    print(f"Adding content identifier to {filepath}")
    filepath = pathlib.Path(filepath)
    temp_filepath = filepath.with_name(f".{asset_id}_{filepath.name}")
    os.rename(filepath, temp_filepath)
    
    with objc.autorelease_pool():
        asset = AVFoundation.AVAsset.assetWithURL_(NSURL.fileURLWithPath_(str(temp_filepath)))
        metadata_item = AVFoundation.AVMutableMetadataItem.metadataItem()
        metadata_item.setKey_("com.apple.quicktime.content.identifier")
        metadata_item.setKeySpace_("mdta")
        metadata_item.setValue_(asset_id)
        metadata_item.setDataType_("com.apple.metadata.datatype.UTF-8")
        
        export_session = AVFoundation.AVAssetExportSession.alloc().initWithAsset_presetName_(
            asset, AVFoundation.AVAssetExportPresetPassthrough
        )
        export_session.setOutputFileType_(AVFoundation.AVFileTypeQuickTimeMovie)
        export_session.setOutputURL_(NSURL.fileURLWithPath_(str(filepath)))
        export_session.setMetadata_([metadata_item])
        
        event = threading.Event()
        def completion_handler():
            os.unlink(temp_filepath) if not export_session.error() else os.rename(temp_filepath, filepath)
            event.set()
        
        export_session.exportAsynchronouslyWithCompletionHandler_(completion_handler)
        event.wait()
    
    return export_session.error().description() if export_session.error() else None

def add_content_identifier_to_img(image_path, new_id, reference_file="q.JPG"):
    print(f"Adding content identifier to {image_path}")
    if not os.path.exists(image_path):
        return
    subprocess.run(["exiftool", "-tagsfromfile", reference_file, "-MakerNotes", image_path], check=True)
    subprocess.run(["exiftool", f"-ContentIdentifier={new_id}", image_path], check=True)

def update_makernotes_and_content_id(folder_path, files):
    for file in files:
        file_path = os.path.join(folder_path, file)
        if not os.path.exists(file_path):
            continue
        
        base_name, _ = os.path.splitext(file)
        mp4_file = f"{base_name}.mp4"
        video_file = f"{base_name}"
        mp4_path = os.path.join(folder_path, mp4_file)
        video_path = os.path.join(folder_path, video_file)
        
        if not (os.path.exists(mp4_path) or os.path.exists(video_path)):
            add_photo_to_icloud(file_path)
            continue
        
        new_id = str(uuid.uuid4()).upper()
        add_content_identifier_to_img(file_path, new_id)
        if os.path.exists(video_path):
            mp4_path = video_path
        add_content_identifier_to_mp4(mp4_path, new_id)
        add_live_photo_to_icloud(file_path, mp4_path)
        
        for old_file in glob.glob(os.path.join(folder_path, "*_original")):
            os.remove(old_file)

def replace_photo_if_exists(folder_path, check_library):
    print(f"Processing folder: {folder_path}")
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        print(f"Processing file: {filename}")
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
            liked = "not found"
            if check_library:
                liked = photo_exists_in_icloud(filename)
            if liked == "not found":
                update_makernotes_and_content_id(folder_path, {filename})
                add_photo_to_album(filename, "New and Duplicates")
            elif "found, liked: true" in liked:
                add_photo_to_album(filename, "Duplicates in Library")
                update_makernotes_and_content_id(folder_path, {filename})
                add_photo_to_album(filename, "Favorite")
            elif "found, liked: false" in liked:
                add_photo_to_album(filename, "Duplicates in Library")
                update_makernotes_and_content_id(folder_path, {filename})
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".mp4"):
            add_photo_to_album(filename, "Duplicates in Library")
            add_photo_to_icloud(os.path.join(folder_path, filename))
            if "found, liked: true" in photo_exists_in_icloud(filename):
                add_photo_to_album(filename, "Favorite")
            else:
                add_photo_to_album(filename, "New and Duplicates")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python script.py <folder_path> [--check-library]")
        sys.exit(1)
    folder_path = sys.argv[1]
    check_library = "--check-library" in sys.argv[2:]  # Optional flag

    album_exists("Imported")

    replace_photo_if_exists(folder_path, check_library)
