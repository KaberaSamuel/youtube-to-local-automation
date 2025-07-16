# script export youtube to m3u file, with a forgiving pattern, forexample:  "Song Title (Live Version)" and "Song Title (Remix)" Should match! This increases the chances of matches but the precision is lower

import subprocess
import json
import os
import re


def get_youtube_playlist_info(playlist_url):
    """
    Fetches titles for videos in a YouTube playlist using yt-dlp.

    Args:
        playlist_url (str): The URL of the YouTube playlist.

    Returns:
        list: A list of original YouTube titles.
              Returns an empty list if there's an error or no videos found.
    """
    print(f"Fetching playlist information from: {playlist_url}")
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
        print(f"Successfully fetched information for {len(youtube_titles)} videos.")
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


def normalize_text_for_comparison(text):
    """
    Normalizes a string for robust comparison by:
    - Lowercasing
    - Removing common suffixes like (Official Video), (MP3_160K), etc.
    - Removing common punctuation and extra spaces.
    """
    normalized = text.lower()

    # Remove common YouTube/Snaptube suffixes and bitrate info
    normalized = re.sub(
        r"\s*(\(|\[)(official\s+)?(audio|video|lyrics?|visualizer|music\s+video|hd|hq|from\s+f1\s*®\s*the\s+movie|mp3_\d+k|m4a_\d+k|mp4_\d+k)(\)|\])\s*",
        "",
        normalized,
        flags=re.IGNORECASE | re.UNICODE,
    )

    # Remove common punctuation and replace with space, then reduce multiple spaces
    normalized = re.sub(r'[.,!?;:\'"“”‘’`~@#$%^&*()_+={}\[\]\\|<>/]', " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    # Remove leading/trailing spaces and hyphens
    normalized = normalized.strip(" -")

    return normalized


def parse_musicolet_m3u_for_filenames(m3u_file_path):
    """
    Parses a Musicolet-exported M3U file to extract and normalize filenames.

    Args:
        m3u_file_path (str): Path to the Musicolet-exported M3U file.

    Returns:
        set: A set of normalized filenames found in the local library.
    """
    local_filenames_normalized = set()
    print(f"Parsing local library M3U file: {m3u_file_path}")
    try:
        with open(m3u_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and EXTINF/comment lines

                # Extract filename from the path
                # Example path: snaptube/download/SnapTube Audio/Lil Yachty - Won_t Diss You(MP3_160K).mp3
                filename_with_ext = os.path.basename(line)

                # Normalize the filename for comparison
                normalized_filename = normalize_text_for_comparison(filename_with_ext)
                if normalized_filename:
                    local_filenames_normalized.add(normalized_filename)
        print(
            f"Extracted and normalized {len(local_filenames_normalized)} unique local filenames."
        )
        return local_filenames_normalized
    except FileNotFoundError:
        print(
            f"Error: Musicolet M3U file not found at '{m3u_file_path}'. Please check the path."
        )
        return set()
    except Exception as e:
        print(f"An unexpected error occurred while parsing local M3U: {e}")
        return set()


if __name__ == "__main__":
    print("--- YouTube Playlist vs. Local Library (Missing Songs Checker) ---")
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
    youtube_titles = get_youtube_playlist_info(youtube_playlist_url)
    if not youtube_titles:
        print("No YouTube videos found or error occurred. Cannot proceed.")
        exit()

    # Get local filenames from Musicolet's M3U
    local_library_normalized_filenames = parse_musicolet_m3u_for_filenames(
        musicolet_m3u_path
    )
    if not local_library_normalized_filenames:
        print(
            "No local songs found in the provided M3U file or error occurred. Cannot proceed."
        )
        exit()

    # Compare and find missing songs
    missing_songs = []
    matched_count = 0

    print("\nComparing YouTube playlist with local library...")
    for yt_title in youtube_titles:
        normalized_yt_title = normalize_text_for_comparison(yt_title)

        # Check for a match
        if normalized_yt_title in local_library_normalized_filenames:
            matched_count += 1
        else:
            # Try a slightly more lenient check for very short titles or common words
            found_lenient = False
            yt_words = set(normalized_yt_title.split())
            if yt_words:  # Only proceed if there are words to compare
                for local_norm_filename in local_library_normalized_filenames:
                    local_words = set(local_norm_filename.split())
                    if (
                        local_words
                        and len(yt_words.intersection(local_words)) / len(yt_words)
                        >= 0.7
                    ):  # 70% word overlap
                        found_lenient = True
                        break

            if not found_lenient:
                missing_songs.append(yt_title)

    print(f"\n--- Comparison Complete ---")
    print(f"Total YouTube songs: {len(youtube_titles)}")
    print(f"Songs found in local library: {matched_count}")
    print(f"Songs potentially missing from local library: {len(missing_songs)}")

    if missing_songs:
        print("\n--- Missing Songs List ---")
        for i, song in enumerate(missing_songs):
            print(f"{i+1}. {song}")

        output_missing_file = "missing_youtube_songs.txt"
        try:
            with open(output_missing_file, "w", encoding="utf-8") as f:
                for song in missing_songs:
                    f.write(song + "\n")
            print(f"\nList of missing songs saved to '{output_missing_file}'")
        except IOError as e:
            print(f"Error saving missing songs list: {e}")
    else:
        print(
            "\nGreat! All songs from your YouTube playlist appear to be in your local library."
        )
