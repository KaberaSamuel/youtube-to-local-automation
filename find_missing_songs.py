import subprocess
import json
import os
import re


def get_youtube_playlist_titles(playlist_url):
    """
    Fetches raw titles for videos in a YouTube playlist using yt-dlp.

    Args:
        playlist_url (str): The URL of the YouTube playlist.

    Returns:
        list: A list of original YouTube titles (strings).
              Returns an empty list if there's an error or no videos found.
    """
    print(f"Fetching YouTube playlist titles from: {playlist_url}")
    try:
        command = ["yt-dlp", "--flat-playlist", "--print-json", playlist_url]
        process = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )

        youtube_titles = []
        for line in process.stdout.strip().split("\n"):
            if line:
                try:
                    video_data = json.loads(line)
                    title = video_data.get("title")
                    if title:
                        youtube_titles.append(title)
                except json.JSONDecodeError:
                    print(
                        f"Warning: Could not decode JSON line from yt-dlp: {line[:100]}..."
                    )
        print(f"Successfully fetched {len(youtube_titles)} YouTube titles.")
        return youtube_titles
    except subprocess.CalledProcessError as e:
        print(f"Error calling yt-dlp: {e}")
        print(f"Stderr: {e.stderr}")
        print("Please ensure yt-dlp is installed and in your system's PATH.")
        print("You can install it using pip: pip install yt-dlp")
        return []
    except FileNotFoundError:
        print("Error: 'yt-dlp' command not found.")
        print("Please ensure yt-dlp is installed and in your system's PATH.")
        print("You can install it using pip: pip install yt-dlp")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while fetching YouTube info: {e}")
        return []


def clean_title_for_comparison(title_string):
    """
    Cleans and normalizes a song title (from YouTube or local filename) for robust comparison.
    This function aims to extract the core artist and song title, stripping away
    suffixes, bitrate info, and standardizing special characters.
    """
    cleaned = title_string.lower()

    # 1. Remove common file extensions (if present, from local filenames)
    cleaned = re.sub(r"\.(mp3|m4a|opus)$", "", cleaned, flags=re.IGNORECASE)

    # 2. Remove common bitrate suffixes (from local filenames)
    cleaned = re.sub(r"\s*\(mp3_\d+k\)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\(m4a_\d+k\)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\(mp4_\d+k\)\s*", "", cleaned, flags=re.IGNORECASE)

    # 3. Remove common YouTube/Snaptube descriptive suffixes (from both)
    # This regex targets common phrases often in parentheses or brackets.
    cleaned = re.sub(
        r"\s*(\(|\[)(official\s+)?(audio|video|lyrics?|visualizer|music\s+video|hd|hq|from\s+f1\s*®\s*the\s+movie)(\)|\])\s*",
        " ",  # Replace with space to separate words
        cleaned,
        flags=re.IGNORECASE | re.UNICODE,
    )

    # 4. Replace non-alphanumeric characters (excluding spaces and hyphens) with a space.
    # This handles all forms of punctuation and Musicolet's `_` replacements.
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", cleaned)

    # 5. Collapse multiple spaces/hyphens into a single space.
    cleaned = re.sub(r"[\s-]+", " ", cleaned)

    # 6. Trim leading/trailing spaces.
    cleaned = cleaned.strip()

    return cleaned


def parse_musicolet_m3u_to_cleaned_titles(m3u_file_path):
    """
    Parses a Musicolet-exported M3U file to extract and clean song titles from filenames.

    Args:
        m3u_file_path (str): Path to the Musicolet-exported M3U file.

    Returns:
        set: A set of cleaned and normalized song titles from the local library.
    """
    local_cleaned_titles = set()
    print(f"Parsing local library M3U file: {m3u_file_path}")
    try:
        with open(m3u_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and EXTINF/comment lines

                # Extract filename from the path
                filename_with_ext = os.path.basename(line)

                # Clean and normalize the filename for comparison
                cleaned_title = clean_title_for_comparison(filename_with_ext)
                if cleaned_title:
                    local_cleaned_titles.add(cleaned_title)
        print(
            f"Extracted and cleaned {len(local_cleaned_titles)} unique local song titles."
        )
        return local_cleaned_titles
    except FileNotFoundError:
        print(
            f"Error: Musicolet M3U file not found at '{m3u_file_path}'. Please check the path."
        )
        return set()
    except Exception as e:
        print(f"An unexpected error occurred while parsing local M3U: {e}")
        return set()


if __name__ == "__main__":
    print(
        "--- YouTube Playlist vs. Local Library (Simplified Missing Songs Checker) ---"
    )
    print(
        "This script will identify songs from your YouTube playlist that are NOT in your local library."
    )
    print("Make sure you have 'yt-dlp' installed (pip install yt-dlp).")

    youtube_playlist_url = input(
        "\nEnter the full URL of your YouTube playlist: "
    ).strip()
    if not youtube_playlist_url:
        print("No YouTube URL provided. Exiting.")
        exit()

    musicolet_m3u_path = input(
        "Enter the full path to your Musicolet-exported M3U file (e.g., C:\\Users\\YourName\\Documents\\MyLibrary.m3u): "
    ).strip()
    if not musicolet_m3u_path:
        print("No Musicolet M3U path provided. Exiting.")
        exit()

    # Get YouTube playlist titles
    youtube_titles_raw = get_youtube_playlist_titles(youtube_playlist_url)
    if not youtube_titles_raw:
        print("No YouTube videos found or error occurred. Cannot proceed.")
        exit()

    # Clean and normalize YouTube titles for comparison
    youtube_cleaned_titles = {
        clean_title_for_comparison(title) for title in youtube_titles_raw
    }

    # Get local cleaned titles from Musicolet's M3U
    local_library_cleaned_titles = parse_musicolet_m3u_to_cleaned_titles(
        musicolet_m3u_path
    )
    if not local_library_cleaned_titles:
        print(
            "No local songs found in the provided M3U file or error occurred. Cannot proceed."
        )
        exit()

    # Compare and find missing songs
    missing_songs_raw = []
    matched_count = 0

    print("\nComparing YouTube playlist with local library...")
    for i, yt_title_raw in enumerate(youtube_titles_raw):
        cleaned_yt_title = clean_title_for_comparison(yt_title_raw)

        if cleaned_yt_title in local_library_cleaned_titles:
            matched_count += 1
        else:
            missing_songs_raw.append(yt_title_raw)  # Append the original YouTube title

    print(f"\n--- Comparison Complete ---")
    print(f"Total YouTube songs: {len(youtube_titles_raw)}")
    print(f"Songs found in local library: {matched_count}")
    print(f"Songs potentially missing from local library: {len(missing_songs_raw)}")

    if missing_songs_raw:
        print("\n--- Missing Songs List ---")
        for i, song in enumerate(missing_songs_raw):
            print(f"{i+1}. {song}")

        output_missing_file = "missing_youtube_songs.txt"
        try:
            with open(output_missing_file, "w", encoding="utf-8") as f:
                for song in missing_songs_raw:
                    f.write(song + "\n")
            print(f"\nList of missing songs saved to '{output_missing_file}'")
        except IOError as e:
            print(f"Error saving missing songs list: {e}")
    else:
        print(
            "\nGreat! All songs from your YouTube playlist appear to be in your local library (based on cleaned titles)."
        )
