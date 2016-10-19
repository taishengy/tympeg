from pympeg import *

## Tools and Utilities - General scripting tools, finding input streams, using time codes ##
def toolsAndUtilities():

    #List of methods used here:
    # MediaObject.getStreamsWithKeys(key)
    # MediaObject.getStreamsWithKeys(key, streamList=)
    # MediaObject.getStreamsWithValue(key, streamList=)
    # concatTimeCode(HH, MM, SS)
    # splitTimeCode(timeCode)
    # subtractTimeCode(timeCode, subTime)
    # timeCodeToSeconds(timeCode)
    # MBtokb(megabytes)

    filePath = 'C:/Media/Sintel.mkv'
    mediaInfo = MediaObject(filePath)
    mediaInfo.run()

    ## Finding Streams with tags ##
    key = 'language'
    print('Streams with the tag ' + key + ' : ' + str(mediaInfo.getStreamsWithKeys(key)))
    print('Subtitle streams with the tag ' + key + ' : ' + str(mediaInfo.getStreamsWithKeys(key, streamList=mediaInfo.subtitleStreams)))
    print()

    key = 'eng'
    print('Streams with the tag ' + key + ' : ' + str(mediaInfo.getStreamsWithValue(key)))
    print('Subtitle streams with the tag ' + key + ' : ' + str(mediaInfo.getStreamsWithValue(key, streamList=mediaInfo.subtitleStreams)))
    print()

    ## Manipulating Timecodes ##
    hours = 1
    minutes = 2
    seconds = 3.456
    timeCode = concatTimeCode(hours, minutes, seconds)

    print("Created timecode: " + str(timeCode))
    HH, MM, SS = splitTimeCode(timeCode)
    print("Hour(s): " + str(HH) + ", Minute(s): " + str(MM) +", Second(s): " + str(SS))

    subtraction = '00:45:14.245'
    remainingTime = subtractTimeCode(timeCode, subtraction)
    print('Time remaining after subtracting ' + subtraction + ' is: ' + remainingTime)

    duration = timeCodeToSeconds(remainingTime)
    print("Duration of remaining time in seconds: " + str(duration))

    filesize = 4.7 # MB
    print(str(filesize) + " MB is " +str(MBtokb(filesize)) + " kilobits")


def toolsAndUtilitiesExplained():
    # Here we'll look at some of the tools to help script things.

    # We must first create a MediaObject of the file to inspect
    filePath = 'C:/Media/Sintel.mkv'
    mediaInfo = MediaObject(filePath)
    mediaInfo.run()

    # MediaObject.getStreamsWithKeys(key, streamList) searches the stream dictionaries for streams with a key. This can
    # be used to find streams with certain tags or information. Below we look for all the streams with a 'language'
    #  association. The streams' index is returned in an array.
    print(str(mediaInfo.getStreamsWithKeys('language')))
    # This returns all the streams, in this case both audio and subtitle stream(s).

    # If we're only interested in the subtitle streams we can specify to only search those streams by
    # passing an array of streams to search.
    print(str(mediaInfo.getStreamsWithKeys('language', streamList=mediaInfo.subtitleStreams)))

    # Likewise, values in the dictionaries can be searched for in the same way.
    print(str(mediaInfo.getStreamsWithValue('eng')))
    # Here, both the audio stream and the english subtitle stream have the value 'eng' associated.

    # Here we can search only the subtitle streams for 'eng'
    print(str(mediaInfo.getStreamsWithValue('eng', streamList=mediaInfo.subtitleStreams)))

    ## Manipulating Timecodes ##
    hours = 1
    minutes = 2
    seconds = 3.456

    # Make a timecode string from numeric components
    timeCode = concatTimeCode(hours, minutes, seconds)
    print("Created timecode: " + str(timeCode))

    # Make numeric components from a timecode
    HH, MM, SS = splitTimeCode(timeCode)
    print("Hour(s): " + str(HH) + ", Minute(s): " + str(MM) +", Second(s): " + str(SS))

    # Subtract two timecodes
    subtraction = '00:45:14.245'
    remainingTime = subtractTimeCode(timeCode, subtraction)
    print('Time remaining after subtracting ' + subtraction + ' is: ' + remainingTime)

    # Find the duration of a timecode in seconds
    duration = timeCodeToSeconds(remainingTime)
    print("Duration of remaining time in seconds: " + str(duration))

    # Get kilobits from Megabytes
    filesize = 4.7 # MB
    print(str(filesize) + " MB is " +str(MBtokb(filesize)) + " kilobits")

## Example 1 - Converting a file with all subtitles ##
def example1():
    filePath = 'C:/Media/Sintel.mkv'
    mediaInfo = MediaObject(filePath)
    mediaInfo.run()

    converter = MediaConverter(mediaInfo, 'C:/Media/Sintel_550.mkv')
    converter.createVideoStream(mediaInfo.videoStreams[0],  'cbr', 'x264', height=550, cbr=1500, speed='slower')
    converter.createAudioStream(mediaInfo.audioStreams[0])
    converter.createSubtitleStreams(mediaInfo.subtitleStreams)
    converter.convert()

def example1Explained():
    # File path to file you want to inspect/convert
    filePath = 'C:/Media/Sintel.mkv'

    # Create a MediaInfo object. This will contain the information ffmpeg needs to do its magic.
    mediaInfo = MediaObject(filePath)

    # Run the mediaInfo object, this call ffprobe and stores and parses the output in dictionaries within the MediaObject
    mediaInfo.run()


    # Create the converter object. It requires a MediaObject, the output path is optional, without it it just makes another
    # file with a prefix on the filename in the source file's directory
    converter = MediaConverter(mediaInfo, 'C:/Media/Sintel720.mkv')

    # Creating Output streams is pretty simple. Audio and video streams take a single stream, if you want multiple audio
    # or video streams you'll need to call createXStream multiple times and set the parameters for each stream. You'll
    # notice a lot of optional parameters. Read up on the encoder parameters of the encoders that interest you.

    # For video we choose the first (and only) video stream. We choose to use a constant bit rate mode, with a bit rate of
    # 1500 kbit/s, scale the resolution to a height of 550, and use the 'slower' encoding speed. Some of the parameters
    # are optional, but you may not like the defaults.
    converter.createVideoStream(mediaInfo.videoStreams[0],  'cbr', 'x264', height=550, cbr=1500, speed='slower')

    # For audio we are again choosing the first and only stream. We allow all the defaults in this case.
    # AAC encoder, 128kbits/s and stereo audio
    converter.createAudioStream(mediaInfo.audioStreams[0])

    # We choose all the subtitles by inputting an array of stream indexes. You could also input indices manually or find
    # streams with key words you want
    converter.createSubtitleStreams(mediaInfo.subtitleStreams)

    # Finally call on ffmpeg to do the conversion and write the streams to the output file.
    converter.convert()

## Example 2 - Cutting a small piece out of a file ##
def example2():
    filePath = 'C:/Media/Sintel.mkv'
    mediaInfo = MediaObject(filePath)
    mediaInfo.run()

    converter = MediaConverter(mediaInfo, 'C:/Media/output/Sintel_550_Clip.mkv')
    converter.createVideoStream(mediaInfo.videoStreams[0],  'cbr', 'x264', height=550, cbr=1500, speed='slower')
    converter.createAudioStream(mediaInfo.audioStreams[0])
    converter.createSubtitleStreams(mediaInfo.subtitleStreams)
    converter.clip('00:02:50', '00:04:30')

## Example 3 - Making a webm with filesize limits ##
def example3():
    filePath = 'C:/Media/output/Sintel_550_Clip.mkv'
    mediaInfo = MediaObject(filePath)
    mediaInfo.run()

    fileSize = MBtokb(3) # converts 3 megabytes to kilobits, ffmpeg likes kilobits, I think in megabytes

    start   = '00:00:20'
    end     = '00:00:45'
    duration = timeCodeToSeconds(subtractTimeCode(end, start))

    audioBitrate = 64 # kb/s
    videoStreamSize = fileSize - (audioBitrate * duration)
    videoBitrate = videoStreamSize / duration

    converter = MediaConverter(mediaInfo, 'C:/Media/output/Sintel_550_net.webm')
    converter.createVideoStream(mediaInfo.videoStreams[0],  'cbr', 'vpx', height=550, cbr=videoBitrate, speed='medium')
    # converter.createAudioStream(mediaInfo.audioStreams[0], audioEncoder='aac', audioBitrate=audioBitrate)

    converter.clip(start, end)

toolsAndUtilities()

# example2()
# example3()