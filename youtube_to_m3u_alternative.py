import subprocess
import json
import os
import re


def get_youtube_playlist_info(playlist_url):
    """
    Fetches titles and durations for videos in a YouTube playlist using yt-dlp.

    Args:
        playlist_url (str): The URL of the YouTube playlist.

    Returns:
        list: A list of dictionaries, each containing 'title' and 'duration' (in seconds).
              Returns an empty list if there's an error or no videos found.
    """
    print(f"Fetching playlist information from: {playlist_url}")
    try:
        command = ["yt-dlp", "--flat-playlist", "--print-json", playlist_url]
        process = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )

        videos_info = []
        for line in process.stdout.strip().split("\n"):
            if line:
                try:
                    video_data = json.loads(line)
                    title = video_data.get("title")
                    duration = video_data.get("duration")  # duration in seconds
                    if title and duration is not None:
                        videos_info.append({"title": title, "duration": int(duration)})
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON line: {line[:100]}...")
        print(f"Successfully fetched information for {len(videos_info)} videos.")
        return videos_info
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
        print(f"An unexpected error occurred: {e}")
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


def parse_musicolet_m3u_for_local_files(m3u_file_path):
    """
    Parses a Musicolet-exported M3U file to extract normalized filenames and their
    original full paths.

    Args:
        m3u_file_path (str): Path to the Musicolet-exported M3U file (containing all local songs).

    Returns:
        dict: A dictionary mapping normalized filename strings to their original
              full paths. Only the first path for a given normalized name is stored.
              Returns an empty dictionary if there's an error or no files found.
    """
    local_files_map = {}
    print(f"Parsing local library M3U file: {m3u_file_path}")
    try:
        with open(m3u_file_path, "r", encoding="utf-8") as f:
            current_path = None
            for line in f:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue  # Skip empty lines and EXTM3U header

                if line.startswith("#EXTINF:"):
                    # This line contains duration and display title. The next line is the path.
                    # We only care about the path for now, but parse EXTINF if needed later.
                    continue
                else:
                    # This line should be the path to the song file
                    current_path = line.replace("\\", "/")  # Normalize path separators

                    if current_path:
                        filename_with_ext = os.path.basename(current_path)
                        normalized_filename = normalize_text_for_comparison(
                            filename_with_ext
                        )
                        if (
                            normalized_filename
                            and normalized_filename not in local_files_map
                        ):
                            local_files_map[normalized_filename] = current_path
                        current_path = None  # Reset for the next entry
        print(
            f"Extracted and normalized {len(local_files_map)} unique local file paths."
        )
        return local_files_map
    except FileNotFoundError:
        print(
            f"Error: Musicolet 'all songs' M3U file not found at '{m3u_file_path}'. Please check the path."
        )
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while parsing local M3U: {e}")
        return {}


def generate_m3u_playlist_with_matching(
    youtube_playlist_info, local_files_map, output_file="youtube_playlist_matched.m3u"
):
    """
    Generates an M3U playlist file using YouTube video information and matching
    them against local files using a forgiving algorithm. Only matched songs are included.

    Args:
        youtube_playlist_info (list): A list of dictionaries with 'title' and 'duration'
                                      from the YouTube playlist.
        local_files_map (dict): A dictionary mapping normalized local filenames to their
                                original full paths.
        output_file (str): The name of the M3U file to create.
    """
    m3u_content = ["#EXTM3U"]
    matched_songs_count = 0

    print(f"\nGenerating M3U file: {output_file}")
    print(
        "This M3U will only contain paths for songs found on your device using a forgiving match."
    )
    print(
        f"IMPORTANT: Place '{output_file}' directly in '/storage/emulated/0/' on your phone."
    )

    for video in youtube_playlist_info:
        yt_title_original = video["title"]
        duration = video["duration"]  # Duration in seconds

        normalized_yt_title = normalize_text_for_comparison(yt_title_original)
        matched_local_path = None

        # Try direct normalized match first
        if normalized_yt_title in local_files_map:
            matched_local_path = local_files_map[normalized_yt_title]
        else:
            # Try lenient word overlap match
            yt_words = set(normalized_yt_title.split())
            if yt_words:
                best_match_score = 0
                for local_norm_filename, local_full_path in local_files_map.items():
                    local_words = set(local_norm_filename.split())
                    if local_words:
                        overlap_score = len(yt_words.intersection(local_words)) / len(
                            yt_words
                        )
                        if (
                            overlap_score >= 0.7 and overlap_score > best_match_score
                        ):  # 70% word overlap threshold
                            best_match_score = overlap_score
                            matched_local_path = local_full_path
                            # print(f"Lenient match for '{yt_title_original}' with '{os.path.basename(local_full_path)}' (Score: {overlap_score:.2f})")

        if matched_local_path:
            # Clean title for display in #EXTINF line (optional, but good practice)
            display_title = yt_title_original  # Use original YT title for display, it's usually cleaner
            # If you want to clean display title more aggressively like previous script:
            # display_title = clean_display_title(yt_title_original)

            m3u_content.append(f"#EXTINF:{duration},{display_title}")
            m3u_content.append(matched_local_path)
            m3u_content.append("")  # Empty line for readability
            matched_songs_count += 1
        # else:
        # print(f"Skipping: No confident match found for '{yt_title_original}'")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
        print(
            f"Successfully created '{output_file}' with {matched_songs_count} matched songs."
        )
        if matched_songs_count < len(youtube_playlist_info):
            print(
                f"Note: {len(youtube_playlist_info) - matched_songs_count} songs from the YouTube playlist could not be confidently matched and were skipped."
            )
    except IOError as e:
        print(f"Error writing M3U file: {e}")


if __name__ == "__main__":
    print("--- YouTube Playlist to Musicolet M3U Generator (Forgiving Match) ---")
    print(
        "This script will create an M3U playlist for Musicolet by matching your YouTube songs"
    )
    print(
        "against your *existing local music files* using a forgiving comparison algorithm."
    )
    print(
        "\nMake sure you have 'yt-dlp' installed on your system (pip install yt-dlp)."
    )

    youtube_playlist_url = input(
        "\nEnter the full URL of your YouTube playlist: "
    ).strip()
    if not youtube_playlist_url:
        print("No YouTube URL provided. Exiting.")
        exit()

    musicolet_all_songs_m3u_path = input(
        "Enter the full path to your Musicolet-exported M3U file containing ALL your songs (e.g., C:\\Users\\YourName\\Documents\\MyLibrary.m3u): "
    ).strip()
    if not musicolet_all_songs_m3u_path:
        print("No Musicolet 'all songs' M3U path provided. Exiting.")
        exit()

    output_m3u_filename = input(
        "Enter desired M3U output filename (e.g., my_matched_playlist.m3u, default: youtube_playlist_matched.m3u): "
    ).strip()
    if not output_m3u_filename:
        output_m3u_filename = "youtube_playlist_matched.m3u"

    # 1. Get YouTube playlist titles and durations
    playlist_data = get_youtube_playlist_info(youtube_playlist_url)
    if not playlist_data:
        print("No YouTube videos found or error occurred. Cannot proceed.")
        exit()

    # 2. Get local file information from Musicolet's exported M3U
    local_files_info = parse_musicolet_m3u_for_local_files(musicolet_all_songs_m3u_path)
    if not local_files_info:
        print(
            "No local songs found in the provided M3U file or error occurred. Cannot proceed."
        )
        exit()

    # 3. Generate the M3U playlist with forgiving matching
    generate_m3u_playlist_with_matching(
        playlist_data, local_files_info, output_m3u_filename
    )

    print("\n--- M3U Generation Complete ---")
    print(f"1. Transfer '{output_m3u_filename}' to your Android phone.")
    print(
        f"   **IMPORTANT:** Place it directly in the root of your internal storage: `/storage/emulated/0/`"
    )
    print("2. Open Musicolet app on your phone.")
    print("3. Go to 'Playlists' section.")
    print(
        "4. Look for an 'Import playlist' or '+' icon and select the transferred M3U file."
    )
    print(
        "Musicolet will now scan your local files based on the paths in the M3U and create your playlist."
    )
    print(
        "\nSongs that could not be confidently matched were skipped from the output M3U."
    )
