#!/usr/bin/env python3
"""
YouTube Playlist to M3U Converter with Automatic File Matching
Usage: python youtube_to_m3u.py <playlist_url> <music_directory> [output_file]
"""

import sys
import subprocess
import json
import re
import os
from pathlib import Path
from difflib import SequenceMatcher
import unicodedata


def normalize_text(text):
    """Normalize text for better matching"""
    # Remove accents and convert to lowercase
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Remove common words and characters that might differ
    text = re.sub(r"\b(official|video|audio|hd|hq|lyrics|lyric|music|song)\b", "", text)
    text = re.sub(r"[^\w\s]", " ", text)  # Replace punctuation with spaces
    text = re.sub(r"\s+", " ", text)  # Multiple spaces to single space
    text = text.strip()

    return text


def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def get_playlist_info(playlist_url):
    """Extract playlist information using yt-dlp"""
    print("Extracting playlist information from YouTube...")
    cmd = ["yt-dlp", "--flat-playlist", "--dump-json", playlist_url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [json.loads(line) for line in result.stdout.strip().split("\n") if line]
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e}")
        return None


def scan_music_files(music_directory):
    """Scan the music directory for audio files"""
    print(f"Scanning music files in: {music_directory}")

    audio_extensions = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".wma"}
    music_files = []

    if not os.path.exists(music_directory):
        print(f"Error: Music directory not found: {music_directory}")
        return []

    for root, dirs, files in os.walk(music_directory):
        for file in files:
            if Path(file).suffix.lower() in audio_extensions:
                full_path = os.path.join(root, file)
                music_files.append(full_path)

    print(f"Found {len(music_files)} audio files")
    return music_files


def match_songs(playlist_info, music_files, threshold=0.6):
    """Match YouTube playlist songs with local music files"""
    print("Matching YouTube songs with local files...")

    matched_songs = []
    unmatched_songs = []

    for i, item in enumerate(playlist_info):
        title = item.get("title", "Unknown")
        uploader = item.get("uploader", "Unknown Artist")
        duration = item.get("duration", 0)

        print(f"Processing {i+1}/{len(playlist_info)}: {title}")

        best_match = None
        best_score = 0

        # Try to match with each music file
        for music_file in music_files:
            filename = os.path.basename(music_file)
            filename_no_ext = os.path.splitext(filename)[0]

            # Calculate similarity scores
            title_score = similarity(title, filename_no_ext)
            full_score = similarity(f"{uploader} {title}", filename_no_ext)

            # Use the better score
            score = max(title_score, full_score)

            if score > best_score:
                best_score = score
                best_match = music_file

        if best_match and best_score >= threshold:
            matched_songs.append(
                {
                    "title": title,
                    "uploader": uploader,
                    "duration": duration,
                    "file_path": best_match,
                    "match_score": best_score,
                }
            )
            print(
                f"  ✓ Matched with: {os.path.basename(best_match)} (score: {best_score:.2f})"
            )
        else:
            unmatched_songs.append(
                {
                    "title": title,
                    "uploader": uploader,
                    "duration": duration,
                    "best_match": best_match,
                    "best_score": best_score,
                }
            )
            print(f"  ✗ No good match found (best score: {best_score:.2f})")

    return matched_songs, unmatched_songs


def create_m3u_file(matched_songs, output_file):
    """Create M3U file from matched songs"""
    print(f"Creating M3U file: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for song in matched_songs:
            title = song["title"]
            uploader = song["uploader"]
            duration = song["duration"]
            file_path = song["file_path"]

            # Write M3U entry
            f.write(f"#EXTINF:{duration},{uploader} - {title}\n")
            f.write(f"{file_path}\n")

    print(f"M3U file created successfully!")


def save_unmatched_report(unmatched_songs, output_file):
    """Save a report of unmatched songs"""
    if not unmatched_songs:
        return

    report_file = output_file.replace(".m3u", "_unmatched.txt")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("UNMATCHED SONGS REPORT\n")
        f.write("=" * 50 + "\n\n")

        for song in unmatched_songs:
            f.write(f"Title: {song['title']}\n")
            f.write(f"Uploader: {song['uploader']}\n")
            f.write(f"Best match score: {song['best_score']:.2f}\n")
            if song["best_match"]:
                f.write(f"Best match file: {os.path.basename(song['best_match'])}\n")
            f.write("-" * 30 + "\n")

    print(f"Unmatched songs report saved: {report_file}")


def create_m3u_simple(playlist_info, output_file, android_music_path):
    """Create M3U file with Android paths (for phone files)"""
    print(f"Creating M3U file: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in playlist_info:
            title = item.get("title", "Unknown")
            uploader = item.get("uploader", "Unknown Artist")
            duration = item.get("duration", 0)

            # Clean title for filename
            clean_title = re.sub(r'[<>:"/\\|?*]', "", title)

            # Write M3U entry
            f.write(f"#EXTINF:{duration},{uploader} - {title}\n")

            # Try common extensions
            for ext in [".mp3", ".m4a", ".aac", ".flac", ".ogg"]:
                file_path = f"{android_music_path}/{clean_title}{ext}"
                f.write(f"{file_path}\n")
                break  # Only add one entry per song

    print(f"M3U file created successfully with {len(playlist_info)} songs!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_to_m3u.py <playlist_url> [output_file]")
        print(
            "Example: python youtube_to_m3u.py 'https://www.youtube.com/playlist?list=PLxxxxx' 'my_playlist.m3u'"
        )
        sys.exit(1)

    playlist_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "playlist.m3u"

    # Android path for Snaptube Audio folder
    android_music_path = "/storage/emulated/0/snaptube/download/Snaptube Audio"

    print("Extracting playlist information from YouTube...")
    playlist_info = get_playlist_info(playlist_url)

    if not playlist_info:
        print("Failed to extract playlist information")
        sys.exit(1)

    print(f"Found {len(playlist_info)} songs in playlist")

    # Create M3U file with Android paths
    create_m3u_simple(playlist_info, output_file, android_music_path)

    print(f"\n" + "=" * 50)
    print("SUCCESS!")
    print(f"M3U file created: {output_file}")
    print(f"Songs in playlist: {len(playlist_info)}")
    print(f"Configured for Android path: {android_music_path}")
    print("\nNext steps:")
    print("1. Transfer the M3U file to your phone")
    print("2. Import it into Musicolet")
    print(
        "3. Musicolet will automatically find matching songs in your Snaptube Audio folder"
    )


if __name__ == "__main__":
    main()
