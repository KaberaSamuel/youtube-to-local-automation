# Get list of downloaded music
with open('/mnt/d/Sam/Docs/DownloadedMusicList.txt', 'r') as downloads:
    downloaded_music_list = []

    # removing filetypes from songname
    for songname in downloads.readlines():
        songname = songname.replace("(MP3_160K).mp3", "").replace("\n", "")
        downloaded_music_list.append(songname)
    downloaded_music_list.sort()


# Get a sorted list of youtube playlist
with open('/mnt/d/Sam/Docs/YoutubePlaylist.txt', 'r') as youtube:
    youtube_playlist = []
    for songname in youtube.readlines():
        youtube_playlist.append(songname.replace("\n", ""))
    youtube_playlist.sort()
