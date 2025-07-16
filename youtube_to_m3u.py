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

        # yt-dlp prints each entry as a separate JSON object per line
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
                    print(
                        f"Warning: Could not decode JSON line: {line[:100]}..."
                    )  # Print first 100 chars
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


def sanitize_filename(title):
    """
    Sanitizes a string to be suitable for a filename, removing invalid characters.
    Also handles the leading underscore for some files.
    """
    # Replace common invalid characters with an underscore or remove them
    sanitized = re.sub(r'[\\/:*?"<>|]', "_", title)
    # Remove leading/trailing spaces
    sanitized = sanitized.strip()
    # Handle the leading underscore if present in the original title
    if title.startswith("_") and not sanitized.startswith("_"):
        sanitized = "_" + sanitized
    return sanitized


def generate_m3u_playlist(playlist_info, output_file="chill_playlist.m3u"):
    """
    Generates an M3U playlist file based on YouTube video information.
    It creates multiple candidate paths for each song to help Musicolet find the file.

    Args:
        playlist_info (list): A list of dictionaries with 'title' and 'duration'.
        output_file (str): The name of the M3U file to create.
    """
    # Base path on your Android phone where Musicolet will look for files
    BASE_ANDROID_PATH = "/storage/emulated/0/snaptube/download/SnapTube Audio/"

    m3u_content = ["#EXTM3U"]

    print(f"\nGenerating M3U file: {output_file}")
    print("Musicolet will try to match these paths on your phone.")

    for video in playlist_info:
        yt_title = video["title"]
        duration = video["duration"]  # Duration in seconds

        # Sanitize the title to create a potential filename
        sanitized_yt_title = sanitize_filename(yt_title)

        # Generate multiple candidate paths for Musicolet to try
        # This covers the various naming conventions from Snaptube
        candidate_filenames = [
            f"{sanitized_yt_title}(MP3_160K).mp3",  # Example: Imagine Dragons - Follow You (Lyric Video)(MP3_160K).mp3
            f"{sanitized_yt_title}.mp3",  # Example: Song Title.mp3 (if no bitrate suffix)
            f"{sanitized_yt_title}(MP4_128K).m4a",  # Example: Song Title(MP4_128K).m4a
            f"{sanitized_yt_title}.m4a",  # Example: Post Malone - Chemical (Official Lyric Video).m4a
        ]

        # Add the EXTINF line once for the YouTube title
        m3u_content.append(f"#EXTINF:{duration},{yt_title}")

        # Add all candidate paths for this song
        for filename in candidate_filenames:
            # Ensure forward slashes for Android paths
            full_android_path = os.path.join(BASE_ANDROID_PATH, filename).replace(
                "\\", "/"
            )
            m3u_content.append(full_android_path)

        # Add an empty line for better readability in the M3U file (optional)
        m3u_content.append("")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
        print(
            f"Successfully created '{output_file}' with {len(playlist_info)} entries."
        )
        print(
            "Each song has multiple candidate paths to increase Musicolet's matching success."
        )
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
