"""
Some small examples on how to use this package to do small things. For more sophisticated uses check under scripts/ or
take a peek at some of the stuff in tools.py.

tools/convert_sub_dirs.py is very useful for converting loosely organized media of varying qualities and is decently
documented.

There's also pretty extensive support for concatenating files (ffconcat, and several functions in tools.py), an easily
extendable object to save HLS streams (StreamSaver), and a pooled converter for batch converting files with low 
resolutions.
"""

from pympeg import *
from os import path

# Tools and Utilities - General scripting tools, finding input streams, using time codes ##
def toolsAndUtilities(file):

    #List of methods used here:
    # MediaObject.getStreamsWithKeys(key)
    # MediaObject.getStreamsWithKeys(key, streamList=)
    # MediaObject.getStreamsWithValue(key, streamList=)
    # concat_timecode(HH, MM, SS)
    # split_timecode(timeCode)
    # subtract_timecodes(timeCode, subTime)
    # timecode_to_seconds(timeCode)
    # seconds_to_timecode(seconds)
    # MBtokb(megabytes)

    filePath = file
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
    timeCode = concat_timecode(hours, minutes, seconds)

    print("Created timecode: " + str(timeCode))
    HH, MM, SS = split_timecode(timeCode)
    print("Hour(s): " + str(HH) + ", Minute(s): " + str(MM) +", Second(s): " + str(SS))

    subtraction = '00:45:14.245'
    remainingTime = subtract_timecodes(timeCode, subtraction)
    print('Time remaining after subtracting ' + subtraction + ' is: ' + remainingTime)

    duration = timecode_to_seconds(remainingTime)
    print("Duration of remaining time in seconds: " + str(duration))

    back_to_timecode = seconds_to_timecode(duration + 55)
    print("Remaining time + 55s: " + back_to_timecode)

    filesize = 4.7 # MB
    print(str(filesize) + " MB is " +str(MBtokb(filesize)) + " kilobits")

def toolsAndUtilitiesExplained(file):
    # Here we'll look at some of the tools to help script things.

    # We must first create a MediaObject of the file to inspect
    filePath = file
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
    timeCode = concat_timecode(hours, minutes, seconds)
    print("Created timecode: " + str(timeCode))

    # Make numeric components from a timecode
    HH, MM, SS = split_timecode(timeCode)
    print("Hour(s): " + str(HH) + ", Minute(s): " + str(MM) +", Second(s): " + str(SS))

    # Subtract two timecodes
    subtraction = '00:45:14.245'
    remainingTime = subtract_timecodes(subtraction, timeCode)
    print('Time remaining after subtracting ' + subtraction + ' is: ' + remainingTime)

    # Find the duration of a timecode in seconds
    duration = timecode_to_seconds(remainingTime)
    print("Duration of remaining time in seconds: " + str(duration))
    
    # Make a timecode from seconds
    back_to_timecode = seconds_to_timecode(duration + 55)
    print("Remaining time + 55s: " + back_to_timecode)

    # Get kilobits from Megabytes
    filesize = 4.7 # MB
    print(str(filesize) + " MB is " +str(MBtokb(filesize)) + " kilobits")

# Example 1 - Converting a file with all subtitles
def example1(file, out_dir):
    filePath = file
    media = MediaObject(filePath)
    media.run()  # Runs the analysis for attributes/stream info. The converter do this too if not called explicitly

    # Create converter object, 2nd param is the output file
    converter = MediaConverter(media, path.join(out_dir, 'Sintel_550.mkv'))
    
    # Create video stream, encode using x264, constant bitrate of 1500, use 'ultrafast preset and scale output to 550pix
    converter.createVideoStream('x264', 'cbr', 1500, speed='ultrafast', height=550)
    
    # Create audio stream, first audio stream, opus encoder at 96k stereo
    converter.createAudioStream(media.audioStreams[0], audioEncoder='opus', audioBitrate=96, audioChannels='stereo')
    
    # This adds all subtitle streams to the output file 
    converter.createSubtitleStreams(media.subtitleStreams)
    
    # Start the conversion
    converter.convert()

# Example 2 - Cutting a small piece out of a file
def example2(file, out_dir):
    # Same as Example 1, but using MediaConverter.clip(start, stop) instead of convert()
    filePath = file
    media = MediaObject(filePath)
    media.run()
    
    converter = MediaConverter(media, path.join(out_dir, 'Sintel_550_Clip.mkv'))
    converter.createVideoStream('x264', 'cbr', 1500, speed='ultrafast', height=550)
    converter.createAudioStream(media.audioStreams[0], audioEncoder='opus', audioBitrate=96, audioChannels='stereo')
    converter.createSubtitleStreams(media.subtitleStreams)
    converter.clip('00:02:50', '00:04:30')

# Example 3 - Making a webm with filesize limits
def example3(file, out_dir):
    media = MediaObject(file)
    outputFilePath = path.join(out_dir, 'Sintel_550.webm')
    media.run()

    fileSize = MBtokb(3) # converts 3 megabytes to kilobits, ffmpeg likes kilobits, I think in megabytes

    start = '00:00:20'
    end = '00:00:45'
    duration = timecode_to_seconds(subtract_timecodes(start, end))

    audioBitrate = 64  # kb/s
    videoStreamSize = fileSize - (audioBitrate * duration)
    videoBitrate = videoStreamSize / duration

    converter = MediaConverter(media, outputFilePath)
    converter.createVideoStream('vp9', 'cbr', videoBitrate)
    converter.createAudioStream(audioStream=converter.mediaObject.audioStreams[0], audioEncoder='opus',
                                audioBitrate=audioBitrate, audioChannels='mono')
    converter.clip(start, end)

media_file = "/media/test/Sintel.mkv"
output_dir = "/media/test/examples/"

toolsAndUtilities(media_file)
example1(media_file, output_dir)
example2(media_file, output_dir)
example3(media_file, output_dir)
