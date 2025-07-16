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
        # Use --flat-playlist to get only video info without downloading
        # --print-json outputs each video's info as a JSON line
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


def sanitize_filename_for_path(title):
    """
    Sanitizes a string to be suitable for a filename in a path.
    This function is less aggressive, retaining descriptive phrases like
    '(Official Audio)' if they are part of the original title, as Snaptube
    often includes them in the actual filename.
    """
    # Replace common invalid characters with an underscore or remove them
    sanitized = re.sub(r'[\\/:*?"<>|]', "_", title)
    # Remove leading/trailing spaces
    sanitized = sanitized.strip()
    # Handle the leading underscore if present in the original title
    if title.startswith("_") and not sanitized.startswith("_"):
        sanitized = "_" + sanitized
    return sanitized


def clean_display_title(title):
    """
    Cleans the title for display in the #EXTINF line, removing common
    descriptive suffixes that are often part of YouTube titles but not
    desired in the player's display name.
    """
    # Regex to remove common suffixes like (Official Audio), (Lyric Video), etc.
    # Flags: re.IGNORECASE for case-insensitive matching, re.UNICODE for broader character support
    cleaned = re.sub(
        r"\s*(\(|\[)(official\s+)?(audio|video|lyrics?|visualizer|music\s+video|hd|hq)(\)|\])\s*",
        "",
        title,
        flags=re.IGNORECASE | re.UNICODE,
    )
    # Remove any remaining leading/trailing spaces or hyphens
    cleaned = cleaned.strip(" -")
    return cleaned


def generate_m3u_playlist(playlist_info, output_file="chill_playlist.m3u"):
    """
    Generates an M3U playlist file based on YouTube video information.
    It creates candidate paths focusing ONLY on Snaptube's MP3 (160K) naming.

    Args:
        playlist_info (list): A list of dictionaries with 'title' and 'duration'.
        output_file (str): The name of the M3U file to create.
    """
    # Base path on your Android phone where Musicolet will look for files
    # This matches your Snaptube download location
    BASE_ANDROID_PATH = "/storage/emulated/0/snaptube/download/SnapTube Audio/"

    m3u_content = ["#EXTM3U"]

    print(f"\nGenerating M3U file: {output_file}")
    print("Musicolet will try to match these paths on your phone.")

    for video in playlist_info:
        yt_title_original = video["title"]
        duration = video["duration"]  # Duration in seconds

        # 1. Clean title for display in #EXTINF line
        display_title = clean_display_title(yt_title_original)

        # 2. Sanitize title for filename, keeping descriptive parts
        filename_base = sanitize_filename_for_path(yt_title_original)

        # Generate ONLY the MP3 (160K) path as requested
        filename = f"{filename_base}(MP3_160K).mp3"

        # Add the EXTINF line with the cleaned display title
        m3u_content.append(f"#EXTINF:{duration},{display_title}")

        # Ensure forward slashes for Android paths
        full_android_path = os.path.join(BASE_ANDROID_PATH, filename).replace("\\", "/")
        m3u_content.append(full_android_path)

        # Add an empty line for better readability in the M3U file (optional)
        m3u_content.append("")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
        print(
            f"Successfully created '{output_file}' with {len(playlist_info)} entries."
        )
        print("Each song now has a single, precise MP3 (160K) candidate path.")
    except IOError as e:
        print(f"Error writing M3U file: {e}")


if __name__ == "__main__":
    print("--- YouTube Playlist to Musicolet M3U Generator ---")
    print("Make sure you have 'yt-dlp' installed on your system.")
    print("If not, install it via pip: pip install yt-dlp")
    print(
        "Or download the executable from: [https://github.com/yt-dlp/yt-dlp/releases](https://github.com/yt-dlp/yt-dlp/releases)"
    )

    youtube_playlist_url = input(
        "\nEnter the full URL of your YouTube playlist: "
    ).strip()
    if not youtube_playlist_url:
        print("No URL provided. Exiting.")
    else:
        output_m3u_filename = input(
            "Enter desired M3U output filename (e.g., chill_music.m3u, default: chill_playlist.m3u): "
        ).strip()
        if not output_m3u_filename:
            output_m3u_filename = "chill_playlist.m3u"

        playlist_data = get_youtube_playlist_info(youtube_playlist_url)
        if playlist_data:
            generate_m3u_playlist(playlist_data, output_m3u_filename)
            print("\n--- M3U Generation Complete ---")
            print(f"1. Transfer '{output_m3u_filename}' to your Android phone.")
            print(
                f"   A good location is inside '/storage/emulated/0/snaptube/download/SnapTube Audio/' or your phone's 'Playlists' folder."
            )
            print("2. Open Musicolet app on your phone.")
            print("3. Go to 'Playlists' section.")
            print(
                "4. Look for an 'Import playlist' or '+' icon and select the transferred M3U file."
            )
            print(
                "Musicolet will now scan your local files based on the paths in the M3U and create your playlist."
            )
        else:
            print(
                "\nCould not retrieve playlist information. M3U file was not generated."
            )
