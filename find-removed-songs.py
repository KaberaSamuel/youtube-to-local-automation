import itertools

# get list of downloaded music
with open('/mnt/d/Sam/Docs/DownloadedMusicList.txt', 'r') as downloads:
    downloaded_music_list = []

    # removing filetypes from songname
    for songname in downloads.readlines():
        songname = songname.replace("(MP3_160K).mp3", "").replace("\n", "")
        downloaded_music_list.append(songname)
    downloaded_music_list.sort()


# get a sorted list of youtube playlist
with open('/mnt/d/Sam/Docs/YoutubePlaylist.txt', 'r') as youtube:
    youtube_playlist = []
    for songname in youtube.readlines():
        youtube_playlist.append(songname.replace("\n", ""))
    youtube_playlist.sort()

# function for finding number of identical characters in a string regardless of order
def findsimilarity(original,modified):
    identical = 0
    for char1,char2 in itertools.zip_longest(original, modified):
        if char1==char2:
            identical += 1

    percent = ((identical)/len(original))*100
    return [round(percent), modified]

# variables to experiment with
downloaded_music_list_1 = downloaded_music_list[:150]
youtube_playlist_1 = youtube_playlist[:150]
dictionary = {}

# function for displaying compared pairs in the dictionary
def displayWorkings():
    for key,value in dictionary.items():
        percent = value[0]

        if 90 <= percent < 100:
            print(key,value, len(key) == len(value[1]), "\n")

    print(f"There are {len(dictionary)} in the dictioanary")


# logic to find the most similar song in modified list
for original in youtube_playlist:
    dictionary[original] = [0,""]
    for modified in downloaded_music_list:
        original_similarity = dictionary[original]
        new_similarity = findsimilarity(original,modified) 
        
        if new_similarity[0] > original_similarity[0]:
            dictionary[original] = new_similarity
        
displayWorkings()