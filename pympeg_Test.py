from pympeg import *

filePath = 'C:/Users/taish/Desktop/weaboo shit/New folder/[HorribleSubs] Berserk - 09 [1080p].mkv'
# filePath = 'C:/Users/taish/Desktop/weaboo shit/New folder/output.mkv'

mediaInfo = MediaObject(filePath)
mediaInfo.run()

for i in range(0, len(mediaInfo.streams)):
    print("Codec of stream " + str(i) + ": " + mediaInfo.streamCodec(i))

print()
print("Video Codec: " + str(mediaInfo.videoCodecs()))
print()

for i in range(0, len(mediaInfo.streams)):
    print(str(mediaInfo.streamInfo(i)))
    print()

value = 'eng'
print("Stream(s) with value '" + value + "' : " + str(mediaInfo.getStreamsWithValue(value)))
value = 'jpn'
print("Stream(s) with value '" + value + "' : " + str(mediaInfo.getStreamsWithValue(value)))

key = 'width'
print("Stream(s) with key '" + key + "' : " + str(mediaInfo.getStreamsWithKeys(key)))

key = 'language'  # Recursive, in "tags"
print("Stream(s) with key '" + key + "' : " + str(mediaInfo.getStreamsWithKeys(key)))

key = 'language'
nestedDictIndex = 1
nestedDict = mediaInfo.streams[nestedDictIndex]
print("Stream " + str(nestedDictIndex) + " " + key + " found to be: " + str(mediaInfo.getValueFromKey(key, nestedDict)))
print()

print("self.codecs[]: " + str(mediaInfo.codecs))
print("self.streamTypes[]: " + str(mediaInfo.streamTypes))
print("self.videoCodec: " + mediaInfo.videoCodec)
print("self.bitrates[]: " + str(mediaInfo.bitrates))
print("self.bitrate: " + str(type(mediaInfo.bitrate)) + " " + str(mediaInfo.bitrate))
print("self.size: " + str(type(mediaInfo.size)) + " " + str(mediaInfo.size))
print()

# notAMediaConverter = MediaConverter(mediaInfo, 'breakdisshit')

convSet = MediaConverter(mediaInfo, 'C:\\Users\\taish\\Desktop\\working_test.mkv')
convSet.createVideoStream(0, 'cbr', 'x264', width=480, cbr=300)
# convSet.createVideoStream(0, videoEncoder='copy', bitrateMode='copy')
convSet.createAudioStream(1, 'opus', 64)
convSet.createSubtitleStreams([2])
# convSet.generateArgsArray()

# convSet.convert()
#
# convSet.clip('00:00:00', '00:00:42')
# print()
# convSet.clip('00:00:18', '00:00:48')
# print()
# convSet.clip(startingTime='00:00:30', endingTime='00:00:45')
# print()
convSet.clip('00:15:00', '00:18:30.5')
print()
