from pympeg import *

# todo write a test for all the timecode manipulation
# todo write test for ffConcat
# todo rewrite tests for MediaConverter.convert() and MediaConverter.clip() to contain combinations of encoders and rate control methods
# todo make sure selecting and skipping streams works! (all tests currently encode ALL the streams, not sure if mapping is correct)

def test_parseStreamCodecs(inputFilePath):
    mediaInfo = MediaObject(inputFilePath)

    for i in range(0, len(mediaInfo.streams)):
        print("Codec of stream " + str(i) + ": " + mediaInfo.streamCodec(i))

    print()
    print("Video Codec: " + str(mediaInfo.videoCodecs()))
    print()


def test_findingStreamsAndTags(inputFilePath):
    mediaInfo = MediaObject(inputFilePath)
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

def test_printMediaObjectAttributes(inputFilePath):
    mediaInfo = MediaObject(inputFilePath)

    print("self.codecs[]: " + str(mediaInfo.codecs))
    print("self.streamTypes[]: " + str(mediaInfo.streamTypes))
    print("self.videoCodec: " + mediaInfo.videoCodec)
    print("self.bitrates[]: " + str(mediaInfo.bitrates))
    print("self.bitrate: " + str(type(mediaInfo.bitrate)) + " " + str(mediaInfo.bitrate))
    print("self.size: " + str(type(mediaInfo.size)) + " " + str(mediaInfo.size))
    print()

def test_MediaConverter_convert(inputFilePath, outputDirectory):
    mediaInfo = MediaObject(inputFilePath)

    converter = MediaConverter(mediaInfo, 'C:/Media/output/working_test.mkv')
    converter.createVideoStream(0, 'cbr', 'x264', width=480, cbr=300)
    converter.createAudioStream(1, 'opus', 64)
    converter.createSubtitleStreams([2])
    # converter.generateArgsArray()

    converter.convert()

def test_MediaConverter_clip(inputFilePath, outputDirectory):
    converter = MediaConverter(inputFilePath)
    converter.createVideoStream(0, 'cbr', 'x264', width=480, cbr=300)
    converter.createAudioStream(1, 'opus', 64)
    converter.createSubtitleStreams([2])
    converter.clip('00:00:00', '00:00:42')
    print()
    converter.clip('00:00:18', '00:00:48')
    print()
    converter.clip(startingTime='00:00:30', endingTime='00:00:45')
    print()
    converter.clip('00:15:00', '00:18:30.5')

def test_renameFile():
    a = []
    a.append('file_name.ext')
    a.append('file_name_1.ext')
    a.append('file_name_01.ext')
    a.append('file_name_32.ext')
    a.append('file_name32.ext')
    a.append('file_name_a.ext')
    a.append('filename.ext')
    
    for name in a:
        print('Filename ' + name + ' renamed to: ' + renameFile(name))

def test_timeCodes():
    tooManyMins = '01:85:20.763'
    decimalMins = '02:45.86:00.168'

    toomanySecs = '1:0:225.621'
    no_hours = '0:34:12'

    print(add_timecodes(tooManyMins, toomanySecs))
    print(subtract_timecodes(toomanySecs, tooManyMins))
    print(str(split_timecode(toomanySecs)))
    print(concat_timecode('03', '25', '42.42'))
    print(simplify_timecode(decimalMins))
    print(simplify_timecode(no_hours))

test_timeCodes()
