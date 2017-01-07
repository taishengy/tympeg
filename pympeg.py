import os
import subprocess
import json
from os import path, getcwd, remove, makedirs
from argparse import Namespace
import warnings

# todo Move away from -b:v and -b:a to b:v:index, etc to enable different bitrates per stream
# todo Implement a self.cbr and self.cbr for MediaConverter class to allow encoding quality queries
# todo createXstream() should be able to handle an array of stream indices (maybe createXStreams()??)
# todo scaling to height width checking with inHeight/outHeight == inWidth/outWidth and outHeight & outWidth type(int)
# todo addTimeCodes and subtractTimeCodes() need 'while number > 60' control flow for carrying digits
# todo should timeCode functions check for decimals in HH and MM sections? need to throw error or write math for them
# todo MediaConverter.setArgArray()
# todo all subtitles are currently 'copy' encoded during conversion
# todo renaming files doesn't work? Found the problem, in __init__ logic of MediaConverter

# todo ArgArray for vpx (cbr, crf, AND vbr)
# todo Add other audio encoders (lamemp3, fdk-aac, flac)
# todo implement ISO-693x for language dictionaries?
# todo STDIN for ffmpeg errors
# todo Print MediaConverter output streams and settings

# todo Mono for opus/aac, it's a real mess right now BECAUSE OF THE BUG DESCRIBED BELOW
# todo opus downmixing to stereo: https://trac.ffmpeg.org/ticket/5718

# todo Longterm
# todo MediaStream objects instead of passing around indexes and stuff
# todo MediaConverterQueue (Queueing, progress reports, error handling, etc...)
# todo MediaConverterQueue, skipping, interrupting, sanity checks?, etc...


def splitTimeCode(timeCode):
    """ Takes a timecode string and returns the hours, minutes and seconds.

    :param timeCode: String of format "HH:MM:SS.S" ex. "01:23:45.6"
    :return: HH (int), MM (int), SS (float)
    """
    HH, MM, SS = timeCode.split(':')

    HH = int(HH)
    MM = int(MM)
    SS = float(SS)
    return HH, MM, SS

def concatTimeCode(HH, MM, SS):
    """ Takes hours, minutes, and seconds, and returns a timecode string in the format of "HH:MM:SS.S".

    :param HH: int, hours
    :param MM: int, minutes
    :param SS: float, seconds
    :return: String of timecode
    """
    HH = str(HH)
    MM = str(MM)
    SS = str(SS)

    if len(HH) < 2:
        HH = '0' + HH
    if len(MM) < 2:
        MM = '0' + MM

    if SS.find('.') > 1:
        wholes, decimals = SS.split('.')
    else:
        wholes = SS

    if len(wholes) < 2:
        SS = '0' + SS

    timeCode = HH + ":" + MM + ":" + SS
    return timeCode

def addTimeCodes(timeCode1, timeCode2):
    """ Adds to timecodes together and returns the sum of them.

    :param timeCode1: string, timecode
    :param timeCode2: string, timecode
    :return: string, timecode sum
    """
    HH, MM, SS = splitTimeCode(timeCode1)
    hh, mm, ss = splitTimeCode(timeCode2)

    s = SS + ss
    m = MM + mm
    h = HH + hh

    if s > 60:
        m += 1
        s = s - 60

    if m > 60:
        h += 1
        m = m - 60

    return concatTimeCode(h, m, s)

def subtractTimeCodes(startTime, endTime):
    """ Subtracts two timecode strings from each other. Returns a timecode. If remaining time is less than one it
        returns '0:00:00.0'

    :param timeCode: String of a timecode that will be subtracted from.
    :param subTime: String of a  timecode that will be subtracting.
    :return: String of a timecode that is the remaining time.
    """
    HH, MM, SS = splitTimeCode(endTime)
    hh, mm, ss = splitTimeCode(startTime)

    s = SS - ss
    m = MM - mm
    h = HH - hh

    if s < 0:
        s += 60
        m -= 1

    if m < 0:
        m += 60
        h -=1

    if h < 0:
        s = m = h = 0

    return concatTimeCode(h, m, s)

def timeCodeToSeconds(timeCode):
    """ Takes a time code and returns the total time in seconds.

    :param timeCode: String of a timecode.
    :return: int, seconds equivalent of the timecode
    """
    HH, MM, SS = splitTimeCode(timeCode)

    MM += HH * 60
    SS += MM * 60

    return SS

def MBtokb(megabytes):
    """ Converts megabytes to kilobits.

    :param megabytes: numeric, megabytes
    :return: numeric, kilobits equivalent.
    """
    kilobytes = megabytes * 8192
    return kilobytes

def renameFile(fileName):
    """ Renames file to file_X.ext where 'X' is a number. Adds '_X' or increments '_X' if already present

    :param fileName: string, the filename with extension
    :return: string, renamed file
    """
    name, ext = path.splitext(fileName)
    index = name.rfind('_')
    number = ''

    for i in range(index + 1, len(name)):
        character = name[i]

        try:
            number += str(int(character))
        except ValueError:
            name += '_1'
            break

    if number != '':
        name = name[0 : index + 1] + str(int(number) + 1)

    fileName = name + ext
    return fileName

def ffConcat(mediaObjectArray, outputFilepath):
    """

    :param mediaObjectArray: Array of mediaObjects in order of concatenation
    :param outputFilepath: String, output file path
    :return: subprocess completion data
    """
    # check and verify all items in array are MediaObjects
    # if not, print an error and return
    for items in mediaObjectArray:
        if type(items) is not MediaObject:
            print("ffConcat needs an array of mediaObject. Item in index " + str(mediaObjectArray.index(items)) +
                  " in the passed array is type '" + str(type(items)) + "'!")
            print()
            print("Aborting pymeg.ffConcat()")
            print()
            return

    # write the temporary list.txt of inputs that the ffmpeg concat demuxer wants
    listFileName = str(os.getcwd()) + "\\tempFfConcat.txt"
    with open(listFileName, 'w') as file:
        for items in mediaObjectArray:
            print(str(items.filePath))
            file.write('file ' + "\'"+ str(items.filePath) + "\'" + '\n')

    # build "ffmpeg concat" string
    # assume all files are same codec/resoultion/params, otherwise ffmpeg will throw it's own error
    ffmpegConcatStr = 'ffmpeg -f concat -safe 0 -i "' + listFileName + '" -c copy ' + outputFilepath

    # subprocess "ffmpeg concat"
    try:
        processData = subprocess.run(ffmpegConcatStr, check=True)
    except subprocess.CalledProcessError as cpe:
        print("Error: CalledProcess in pympeg.ffConcat()")
        print("CalledProcessError: " + str(cpe))
    finally:
        os.remove(listFileName)

    return processData

def makeMediaObjectsInDirectory(directory, selector=None):

    def conditionDirectoryString(directoryString):
        if type(directoryString) is not str:
            print("That's not a string that points to a directory, is type " + str(type(directoryString)))
            return
        if directoryString.endswith("/"):
            return directoryString
        else:
            return directoryString + "/"

    directory = conditionDirectoryString(directory)
    mediaObjectArray = []
    fileExtensions = ['.mp4', '.mkv', '.avi', '.m4v', '.wmv', '.webm', '.flv', '.mov', '.mpg', '.mpeg', '.ogg', '.ogv']

    for fileNames in os.listdir(directory):
        if any(extensions in fileNames for extensions in fileExtensions):
            print(fileNames)
            mediaInfo = MediaObject(directory + fileNames)
            mediaInfo.run()
            mediaObjectArray.append(mediaInfo)

    return mediaObjectArray

class MediaConverterQueue():
    def __init__(self, logDirectory):
        self.jobList = []
        self.logDirectory = logDirectory

    def addJob(self, job):
        self.jobList.append(job)

    def addJobs(self, jobs):
        for job in jobs:
            self.jobList.append(job)

    def jobsDone(self):
        if len(self.jobList) < 1:
            print("Job's done!")
        else:
            print("Next job is: " + self.jobList[0].fileName)
        pass

    def jobCanceled(self):
        print("Job canceled.")

    def writeToLog(self, logText):
        pass

    def openLog(self):
        pass

class MediaConverter():
    """ Holds settings that get turned into an arg array for ffmpeg conversion
    """
    def __init__(self, mediaObject, outputFilePath=''):
        """ Generates a ConversionSettings object. Populate fields with createXSettings() Methods.

        :param mediaObject:  ConversionSettings
        :param outputFilePath: string
        :return:
        """
        # general conversion settings
        self.mediaObject = mediaObject

        self.inputFilePath = self.mediaObject.format['filename']
        self.inputFileName = path.basename(self.inputFilePath)
        dir, fileName = path.split(self.mediaObject.filePath)

        # todo FIX RENAMING LOGIC HERE! FILE IS ONLY RENAMED IF outputFilePath IS NOT SPECIFIED
        if outputFilePath == '':
            fileName = "/" + "[Py]" + str(fileName)
            outputFilePath = dir + fileName
        else:
            if path.isfile(outputFilePath):
                fileName = renameFile(fileName)
                outputFilePath = dir + fileName

        self.outputFilePath = outputFilePath

        self.inputFileName = path.basename(outputFilePath)

        self.videoStreams = []
        self.audioStreams = []
        self.subtitleStreams = []

        # todo attachment streams
        self.attachmentStreams = []

        # todo other streams
        self.otherStreams = []

        self.argsArray = ['ffmpeg']

    def convert(self):
        # generate argsArray if not already done
        if self.argsArray == ['ffmpeg']:
            self.generateArgsArray()

        # Make sure the target directory exists!
        outputDirectory, outputFilename = path.split(self.outputFilePath)
        if not os.path.isdir(outputDirectory):
            os.mkdir(outputDirectory)

        subprocess.run(self.argsArray)

    def clip(self, startingTime, endingTime):
        self.generateArgsArray(startTime=startingTime, endTime=endingTime)
        print(self.argsArray)

        self.convert()

    def createVideoStream(self, videoStream, bitrateMode, videoEncoder, width=-1, height=-1,
                            cbr=-1, crf=-1, speed=''):
        """Populates the ConversionSettings object with information on how to transcode video.

        :param videoStreamIndex: int
        :param bitrateMode: string, either cbr or crf
        :param videoEncoder: string, see supportedEncoders[]
        :param width: int, x resolution
        :param height: int, y resolution
        :param cbr: int, bitrate in bits/second
        :param crf: int, constant rate factor between 0-50::lossless-lossy
        :param speed: string, x264 and x265 speed settings, see speedTypes[]
        :return:
        """
        # todo allow encoding multiple videostreams at different resolutions/rates/modes/codecs
        # todo implement lossless=True, changes lots of stuff up

        videoSettingsDict = {}

        # Video Stream selection
        if isinstance(videoStream, int):
            if self.mediaObject.streams[videoStream]['codec_type'] == 'video':
                    videoSettingsDict.update({'videoStream': videoStream})
            else:
                warnings.warn("Stream " + str(videoStream) + " is not a video stream. Defaulting to first video stream"
                                                             "in MediaObject.")
                videoSettingsDict.update({'videoStream': self.mediaObject.videoStreams[0]})
        elif videoStream is None:
            warnings.warn("No video requested.")
        else:
            warnings.warn("Video stream specified not understood, won't be included.")
            return

        supportedEncoders = ['x264', 'x265', 'vpx', 'copy'] # todo test three encoders

        if videoEncoder in supportedEncoders:
            videoSettingsDict.update({'videoEncoder': videoEncoder})
        else:
            ValueError(videoEncoder + " is not supported. Currently supported encoders are: " + str(supportedEncoders))

        # Set resolution from parameter, default same resolution as source
        if (width == -1 and height == -1) or videoEncoder == 'copy':
            # get resolution from self.mediaObject
            videoSettingsDict.update(
                {'width': int(self.mediaObject.streams[self.mediaObject.videoStreams[videoStream]]['width'])})
            videoSettingsDict.update(
                {'height': int(self.mediaObject.streams[self.mediaObject.videoStreams[videoStream]]['height'])})

        else:  # Set by parameters
            videoSettingsDict.update({'width': int(width)})
            videoSettingsDict.update({'height': int(height)})

        if videoEncoder == 'copy':
            self.videoStreams.append(videoSettingsDict)
            self.printVideoSettings()
            return

        # cbr or crf, set values
        if bitrateMode == 'cbr':
            videoSettingsDict.update({'bitrateMode': bitrateMode})

            if cbr == -1:
                raise ValueError("No desired bitrate specified with constant bitrate encoding selected. Please"
                                 " specify a bitrate in createVideoSetting(... cbr= ...)")

            if isinstance(cbr, float):
                cbr = int(round(cbr))
            elif not isinstance(cbr, int):
                raise ValueError("'cbr' parameter not understood. Desired bitrate should be float or int.")

            videoSettingsDict.update({'cbr': cbr})

        elif bitrateMode == 'crf':
            videoSettingsDict.update({'bitrateMode': bitrateMode})

            if crf == -1:
                raise ValueError("No desired rate factor specified with constant rate factor encoding selected. Please"
                                 " specify a rate factor with createVideoSetting(... crf= ...)")
            if not (isinstance(crf, float) or isinstance(crf, int)) or crf < 0 or crf > 49:
                raise ValueError("'crf' parameter not understood. Constant Rate Factor must "
                                 "be an integer between 0 and 49")
            if isinstance(crf, float):
                crf = int(round(crf))
            videoSettingsDict.update({'crf': crf})

        else:
            raise ValueError("No rate control method indicated. Please specify"
                             " createVideoStream(bitRateMode= cbr OR crf) and a rate control target")

        speedTypes = ['placebo', 'veryslow', 'slower', 'slow', 'medium', 'fast', 'faster',
                      'veryfast', 'superfast', 'ultrafast']
        if speed == '':
            videoSettingsDict.update({'speed': speedTypes[9]})
            warnings.warn("No speed specified, default encoding speed set to: " + videoSettingsDict['speed'])
        elif speed in speedTypes:
            videoSettingsDict.update({'speed': speed})
        else:
            ValueError("Speed type: " + speed + " is not supported. Currently supported encoders are: " +
                       str(speedTypes))

        self.videoStreams.append(videoSettingsDict)
        self.printVideoSettings()

    def printVideoSettings(self):
        """ Prints the video settings of the ConversionSettings object.

        :return:
        """
        print("---- VIDEO SETTINGS -----")
        for stream in self.videoStreams:
            print('Stream:  ' + str(stream['videoStream']))
            print('self.width: ' + str(stream['width']))
            print('self.height: ' + str(stream['height']))
            print('self.videoEncoder: ' + str(stream['videoEncoder']))

            if str(stream['videoEncoder']) != 'copy':
                print('self.speed: ' + str(stream['speed']))
                print('self.bitrateMode: ' + str(stream['bitrateMode']))

                if str(stream['bitrateMode']) == 'cbr':
                    print('self.cbr: ' + str(stream['cbr']) + " kbits/s")
                elif str(stream['bitrateMode']) == 'crf':
                    print('self.crf: ' + str(stream['crf']))

            print()

    def createAudioStream(self, audioStream=None, audioEncoder='', audioBitrate=128, audioChannels='stereo'):
        """ Populates the ConversionSettings object with information on how to transcode video.

        :param audioStreams: array[int], values correspond to index of MediaObject.streams[]. Specify None for no audio stream.
        :param audioCodec: string, audio codec to be used to encode audio
        :param audioBitrate: desired audio bitrate in kbit/s
        :param audioChannels: string, 'mono' or 'stereo'
        :return:
        """

        # todo selectable audio codecs (libfaac, mpg3, theora, opus)
        # todo allow arbitrary audio stream settings for an arbitrary number of streams, like with video

        audioSettingsDict = {'audioStream': '', 'audioEncoder': 'aac', 'audioBitrate': 128, 'audioChannels': audioChannels}

        # Audio Stream selection
        if isinstance(audioStream, int):
            if self.mediaObject.streams[audioStream]['codec_type'] == 'audio':
                    audioSettingsDict.update({'audioStream': audioStream})
            else:
                warnings.warn("Stream " + str(audioStream) + " is not an audio stream. It will not be included in the output file.")
                return
        elif audioStream is None:
            warnings.warn("No audio requested.")
        else:
            warnings.warn("Audio Stream specified not understood, won't be included.")
            return

        # Select audio encoder
        supportedAudioEncoders = ['aac', 'opus', 'vorbis'] # todo test three encoders

        if audioEncoder in supportedAudioEncoders:
            audioSettingsDict.update({'audioEncoder': audioEncoder})
        elif audioEncoder == '':
            audioEncoder = 'aac'
        else:
            warnings.warn(audioEncoder + " is not supported or recognized. Currently supported encoders are: "
                       + str(supportedAudioEncoders) + ". Defaulting to aac encoding.")
            audioEncoder = 'aac'

        # Select BitRate
        if isinstance(audioBitrate, int):
            audioSettingsDict.update({'audioBitrate': audioBitrate})
        elif isinstance(audioBitrate, float):
            audioSettingsDict.update({'audioBitrate': int(round(audioBitrate))})
        else:
            warnings.warn("Specified audio bitrate not valid or recognized, defaulting to 128 kbit/s")
            self.audioBitrate = 128


        # Channels
            audioSettingsDict.update({'audioChannels': audioChannels})
            #todo implement channels (stereo, mono, 5.1, etc...)

        self.audioStreams.append(audioSettingsDict)
        self.printAudioSetting()

    def printAudioSetting(self):
        """ Prints the audio settings of the ConversionSettings object.

        :return:
        """
        print('---- AUDIO SETTINGS ----')
        for stream in self.audioStreams:
            print('Stream: ' + str(stream['audioStream']))
            print('audioEncoder: ' + str(stream['audioEncoder']))
            print('audioBitrate: ' + str(stream['audioBitrate']))
            print('audioChannels: ' + str(stream['audioChannels']))
            print()

    def createSubtitleStreams(self, subtitleStreams=[]):
        """ Populates the ConversionSettings object with information on how to encode subtitles

        :param subtitleStreams:
        :return:
        """
        self.subtitleStreams = subtitleStreams

    def generateArgsArray(self, startTime='0', endTime='0'):
        """ Generates the argArray to feed ffmpeg. Generates from the output stream information provided in the
            self.createXstream() methods.

        :param startTime: String, input start time for encoding in format HH:MM:SS.SS
        :param endTime: String, input end time for encoding in format HH:MM:SS.SS
        :return:
        """
        def mapStreamsByType(someStreams, streamCount, fileIndex, argsArray):
            """ Writes the -map stream to the argArray. Look at how it's called below.

            :param someStreams:
            :param streamCount:
            :param fileIndex:
            :param argsArray:
            :return:
            """
            for stream in someStreams:
                argsArray.append('-map')
                argsArray.append(fileIndex + str(streamCount))
                streamCount += 1
            return streamCount

        def addArgsToArray(newArgs, array):
            """ Ensures proper array index formatting. Splits arg strings into seperate array indexes.

            :param newArgs:
            :param array:
            :return:
            """
            if isinstance(newArgs, str):
                newArgs = newArgs.split(" ")
            for arg in newArgs:
                if arg != '':
                    array.append(arg)

        def fastSeek(startTime, endTime):

            fastSeekTime = subtractTimeCodes( startTime,'00:00:30')
            startTime = subtractTimeCodes(startTime, fastSeekTime)
            endTime = subtractTimeCodes(endTime, fastSeekTime)

            print("Fast Seeking To: " + fastSeekTime + " from " + startTime)
            print("Encoding from " + startTime + " to " + endTime + " after fastSeeking.")
            print("Encoding " + subtractTimeCodes(startTime, endTime) + " of media.")
            return fastSeekTime, startTime, endTime

        if (startTime != '0') and (endTime != '0'):
            fastSeekTime, startTime, endTime = fastSeek(startTime, endTime)
            addArgsToArray('-ss ' + fastSeekTime, self.argsArray)
            addArgsToArray('-i', self.argsArray)

            self.argsArray.append(str(self.mediaObject.filePath))

            addArgsToArray('-ss ' + startTime, self.argsArray)
            addArgsToArray('-to ' + endTime, self.argsArray)

        else:
            addArgsToArray('-i', self.argsArray)
            self.argsArray.append(str(self.mediaObject.filePath))

        addArgsToArray('-v', self.argsArray)
        addArgsToArray('24', self.argsArray)

        streamCount = 0
        fileIndex = '0:'

        # -map each stream
        streamCount = mapStreamsByType(self.videoStreams, streamCount, fileIndex, self.argsArray)
        streamCount = mapStreamsByType(self.audioStreams, streamCount, fileIndex, self.argsArray)
        streamCount = mapStreamsByType(self.subtitleStreams, streamCount, fileIndex, self.argsArray)
        streamCount = mapStreamsByType(self.attachmentStreams, streamCount, fileIndex, self.argsArray)
        streamCount = mapStreamsByType(self.otherStreams, streamCount, fileIndex, self.argsArray)

        print("Conversion argArray after stream mapping: " + str(self.argsArray))

        # Video Streams and their args
        vidStrings = []
        ffVideoEncoderNames = {'x264': 'libx264',
                               'x265': 'libx265',
                               'vpx': 'libvpx',
                               'copy': 'copy'}

        for stream in self.videoStreams:
            if stream['videoEncoder'] == 'copy':
                addArgsToArray('-c:v copy', self.argsArray)
                vidStrings.append('-c:v copy')
            else:
                vidString = ' -c:v ' + ffVideoEncoderNames[stream['videoEncoder']]

                if stream['bitrateMode'] == 'cbr':
                    vidString += ' -b:v ' + str(stream['cbr']) + 'k'
                elif stream['bitrateMode'] == 'crf':
                    vidString += ' -crf ' + str(stream['crf'])

                vidString += ' -vf scale=' + str(stream['width']) + ":" + str(stream['height'])

                vidString += ' -preset ' + str(stream['speed'])

                addArgsToArray(vidString, self.argsArray)
                vidStrings.append(vidString)

            print('Video stream ' + str(stream['videoStream']) + ' ffmpeg arguments:' + str(vidStrings[-1]))

        print("Conversion argArray after video stream(s): " + str(self.argsArray))

        # Audio Streams and their args
        audioStrings = []
        ffAudioEncoderNames = {'aac': 'aac',
                               'opus': 'libopus',
                               'vorbis': 'libvorbis',
                               'copy': 'copy'}

        for stream in self.audioStreams:
            if stream['audioEncoder'] == 'copy':
                addArgsToArray(' -c:a copy', self.argsArray)
                audioStrings.append(' -c:a copy')
            else:
                # audioString = '-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']])

                if stream['audioChannels'] == 'abx':
                    if stream['audioEncoder'] == 'opus':
                        # if None:
                        addArgsToArray('-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']]), self.argsArray)

                        # if stereo:
                        # addArgsToArray('-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']] + ' -ac 1'), self.argsArray)
                        # if mono:
                        #   addArgsToArray('-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']] + ' -ac 1'), self.argsArray)
                        addArgsToArray('-b:a ' + str(stream['audioBitrate']) + 'k ', self.argsArray)

                    # addArgsToArray('-filter_complex', self.argsArray)
                    # self.argsArray.append(" [0:" + str(stream['audioStream']) + ".0] [0:" + str(stream['audioStream']) + ".1] amerge ")
                    # addArgsToArray('-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']] + ' -ac 1'), self.argsArray)
                    # addArgsToArray('-b:a ' + str(stream['audioBitrate']) + 'k ', self.argsArray) # + str(stream['audioChannels']), self.argsArray)

                    # audioString += ' -filter_complex pan=1c|c0=0.5*c0+0.5*c1' + ' -ac 1'
                    # audioString += ' -filter_complex' +  " [0:" + str(stream['audioStream']) + ".0] [0:" + str(stream['audioStream']) + ".1] amerge"
                    # audioString += ' -filter_complex "[0:' + str(stream['audioStream']) + '.0:a][0:' + str(stream['audioStream'] - 1) + '.1:a]amix" -ac 1'

                else: # stereo
                    addArgsToArray('-c:a ' + str(ffAudioEncoderNames[stream['audioEncoder']]), self.argsArray)


                # audioString += ' -b:a ' + str(stream['audioBitrate']) + 'k ' # + str(stream['audioChannels'])

                    addArgsToArray('-b:a ' + str(stream['audioBitrate']) + 'k ', self.argsArray) # + str(stream['audioChannels']), self.argsArray)
                # audioStrings.append(audioString)

        print("Conversion argArray after audio stream(s): " + str(self.argsArray))

        for stream in self.subtitleStreams:
            # if self.mediaObject.subtitleStreamTypes[stream]
            addArgsToArray('-c:s copy', self.argsArray)

        print("Conversion argArray after subtitle stream(s): " + str(self.argsArray))

        self.argsArray.append(self.outputFilePath)
        print("Conversion argArray after output file: " + str(self.argsArray))

    def estimateVideoBitrate(self, targetFileSize, startTime=-1, endTime=-1, audioBitrate=-1, otherBitrates=0):

        if startTime == -1 and endTime == -1:
            duration = timeCodeToSeconds(self.mediaObject.duration)
        else:
            duration = timeCodeToSeconds(subtractTimeCodes(startTime, endTime))

        if audioBitrate == -1:
            if self.audioStreams != []:
                audioBitrate = 0
                for audioStream in self.audioStreams:
                    audioBitrate += (audioStream['audioBitrate'])
            else:
                audioBitrate = 128
                print("No audioBitrate specified for estimation, defaulting to 128kbit/s")

        estimatedBitrate = targetFileSize/duration - (audioBitrate + otherBitrates)

        return estimatedBitrate

    def createAttachementSettings(self, mediaObject):
        pass

    def createOtherSettings(self, mediaObject):
        pass

class MediaObject():
    """ An object that holds information relevant to manipulating and transcoding a file with ffmpeg. Uses ffprobe to
     find information and stores it as nested dictionaries in MediaObject.streams[] and MediaObject.format{}.
     Contains methods to help find keys and/or values in streams and streams with keys and/or values.

    """
    def __init__(self, filePath):
        """ Initializes attributes that the MediaObject will contain.

        :param filePath: string, filepath of file to create object over.
        :return:
        """
        self.filePath = filePath
        self.directory, self.fileName = path.split(self.filePath)
        self.ffprobeOut = ''
        self.fileIsValid = True

        # Set by parseStreams()
        self.streams = []
        self.videoStreams = []
        self.audioStreams = []
        self.subtitleStreams = []
        self.attachmentStreams = []
        self.unrecognizedStreams = []

        # Set by parseMetaInfo()
        self.format = {}        # Done
        self.duration = 0       # Done
        self.codecs = []        # Done
        self.streamTypes = []   # Done
        self.videoCodec = ''    # Done
        self.bitrates = []      # Done
        self.bitrate = 0        # Done
        self.size = 0           # Done
        self.langauges = {}     # todo Add some library matching or something for abbreviations, japan=japanese=jpn=jap etc...

    def run(self):
        """ Calls ffprobe and extracts media information from it's output. Then calls methods to parse the information
         into self.streams[] and self.format{}. Stores ffprobe output as self.ffprobeOut.

        :return:
        """

        if not path.isfile(self.filePath):
            warnings.warn("File specified at " + str(self.filePath) + " does not exist or can't be found!")
            return

        argsArray = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-i', self.filePath]
        try:
            self.ffprobeOut = subprocess.check_output(argsArray).decode("utf-8")
        except subprocess.CalledProcessError as cpe:
            warnings.warn("CalledProcessError with " + self.filePath + " in MediaObject.run()."
                                                                       " File is likely malformed or invalid.")
            print("CalledProcessError: " + str(cpe))
            print()
            self.fileIsValid = False

        if self.fileIsValid:
            print("Created MediaObject of: " + str(self.filePath))
            self.parseStreams()
            self.parseMetaInfo()

    def parseStreams(self):
        """ Turns the ffprobe json stream output into nested dictionaries stored as a list at self.streams[{}]. Sorts
         streams into seperate lists based on type (audio, video, etc...). Lists of types integers that correspond to
         the index of self.streams[].

        :return:
        """
        ffProbeInfo = json.loads(self.ffprobeOut, object_hook=lambda d: Namespace(**d))

        i = 0
        for stream in ffProbeInfo.streams:
            streamDict = {}
            self.streams.append(streamDict)
            self.namespaceToDict(stream, '', -1, self.streams[i])
            i += 1

        for stream in self.streams:

            if stream['codec_type'] == "video":
                # print("Stream " + str(stream['index']) + " is a video stream.")
                self.videoStreams.append(stream['index'])
            elif stream['codec_type'] == "audio":
                # print("Stream " + str(stream['index']) + " is a audio stream.")
                self.audioStreams.append(stream['index'])
            elif stream['codec_type'] == "subtitle":
                # print("Stream " + str(stream['index']) + " is a subtitle stream.")
                self.subtitleStreams.append(stream['index'])
            elif stream['codec_type'] == "attachment":
                # print("Stream " + str(stream['index']) + " is an attachment stream.")
                self.attachmentStreams.append(stream['index'])
            else:
                # print("Stream " + str(stream['index']) + " is an unrecognized stream.")
                self.unrecognizedStreams.append(stream['index'])

        # print("Index of video streams: " + str(self.videoStreams))
        # print("Index of audio streams: " + str(self.audioStreams))
        # print("Index of subtitle streams: " + str(self.subtitleStreams))
        # print("Index of attachment streams: " + str(self.attachmentStreams))
        # print("Index of unrecognized streams: " + str(self.unrecognizedStreams))
        # print()

        return self.streams

    def streamInfo(self, streamIndex):
        # todo Make this usefull
        return self.streams[streamIndex]

    def streamCodec(self, streamIndex):
        """ Gets the codec of the stream specified by the streamIndex parameter

        :param streamIndex: int, corresponds to the self.streams[] array.
        :return: string, name of codec used to encode stream
        """

        codec = self.streams[streamIndex]['codec_name']
        return codec

    def videoCodecs(self):
        """ Gets the codecs of all video streams.

        :return: array[str], an array of the names of codecs used to encode video streams.
        """
        streamArray = []

        i=0
        for i in range(0, len(self.streamTypes)):
            if self.streamTypes[i] == 'video':
                streamArray.append(self.codecs[i])

        return streamArray

    def getStreamsWithValue(self, value, streamList=''):
        """ Finds streams with values in them and returns their self.streams[] indices in an array.

        :param value: string or number, the value that you want to find in the stream dictionaries.
        :return: array[int], an array of integers whose values correspond to the self.streams[] array that the value
        was found in.
        """
        def isValueInStream(nestedDict, value, prepath=()):
            for keys, values in nestedDict.items():
                path = prepath + (keys,)
                if values == value: # found value
                    return True
                elif hasattr(values, 'items'): # v is a dict
                    p = isValueInStream(values, value, path) # recursive call
                    if p is not None:
                        return p
        streams = []
        if streamList == '':
            streams = self.streams
        else:
            for stream in streamList:
                streams.append(self.streams[int(stream)])

        streamArray = []
        for stream in streams:
            if isValueInStream(stream, value):
                streamArray.append(stream['index'])
        return streamArray

    def getStreamsWithKeys(self, key, streamList=''):
        """ Finds streams with the specified key in them and returns their self.streams[] indices in an array.

        :param key: string, the value that you want to find in the stream dictionaries.
        :return: array[int], an array of integers whose values correspond to the self.streams[] array that the key
        was found in.
        """
        def isKeyInStream(nestedDict, key, prepath=()):
            for keys, values in nestedDict.items():
                path = prepath + (keys,)
                if keys == key: # found value
                    return True
                elif hasattr(values, 'items'): # v is a dict
                    p = isKeyInStream(values, key, path) # recursive call
                    if p is not None:
                        return p


        streamArray = []
        streams = []
        if streamList == '':
            streams = self.streams
        else:
            for stream in streamList:
                streams.append(self.streams[int(stream)])

        for stream in streams:
            if isKeyInStream(stream, key):
                streamArray.append(stream['index'])
        return streamArray

    def getValueFromKey(self,  key, stream):
        """ Gets the value associated with a key from a stream or format dictionary.

        :param streamDict: dict, dictionary of stream from self.streams[]
        :param key: key of the value to be found
        :return: string, value associated with key. If key was not found value is None
        """

        streamDict = {}

        if isinstance(stream, int):
            streamDict = self.streams[stream]
        elif isinstance(stream, dict):
            streamDict = stream
        else:
            print('getValueFromKey(): stream parameter not understood. Should be a stream dictionary'
                  ' or a list index of a stream.')

        if key in streamDict:
            return streamDict[key]
        for k, v in streamDict.items():
                if isinstance(v, dict):
                    item = self.getValueFromKey(key, v)
                    if item is not None:
                        return item

    def parseMetaInfo(self):
        """ Parses ffprobe json output and builds the self.format{} dictionary. Also sets some useful attributes like
        filesize, bitrate, codecs, etc...

        :return:
        """

        ffProbeInfo = json.loads(self.ffprobeOut, object_hook=lambda d: Namespace(**d))
        self.namespaceToDict(ffProbeInfo.format, '', -1, self.format)
        self.bitrate = int(self.format['bit_rate'])
        self.duration = float(self.format['duration'])
        self.size = int(self.format['size'])

        for stream in self.streams:

            # Setting self.codecs[],
            try:
                self.codecs.append(stream['codec_name'])
            except KeyError:
                print("codec_name not found in stream " + str(stream['index']))
                print("     codecs[" + str(stream['index']) + "] set to 'unknown'.")
                self.streamTypes.append('unknown')

            # Setting self.streamTypes[]
            try:
                self.streamTypes.append(stream['codec_type'])
            except KeyError:
                print("codec_type not found in stream " + str(stream['index']))
                print("     streamTypes[" + str(stream['index']) + "] set to 'unknown'.")
                self.streamTypes.append('unknown')

            # Setting self.bitrates[]
            try:
                bps = self.getValueFromKey('bit_rate', stream)
                if bps is not None:
                    self.bitrates.append(int(bps))
                else:
                    try:
                        bps = self.getValueFromKey('BPS', stream)
                        if bps is not None:
                            self.bitrates.append(int(bps))
                    finally:
                        if bps is None:
                            self.bitrates.append(0)

            except KeyError:
                print("Bitrate not found in stream " + str(stream['index']))

        # warnings.warn("self.bitrates[] is currently unreliable, particularily if a file has already been transcoded.")

        # Set self.videoCodec
        vidcodecs = self.videoCodecs()
        if len(vidcodecs) > 1:
            self.videoCodec = warnings.warn("self.videoCodec(): There are more than one video streams present, " \
                              "please use self.videoCodecs to view multiple video stream codecs.")
        else:
            self.videoCodec = vidcodecs[0]

    def namespaceToDict(self, data, key, level, streamDict):
        """ Transforms namespace extracted from ffprobe json into a nested dictionary strucutre for polling later.

        :param data: Namespace or dictionary
        :param key: string, can be empty (should be for top levels)
        :param level: int, keeps track of level of nested dictionary during traversal
        :param streamDict: the dictionary that is being created as namespaces are converted
        :return:
        """

        level += 1
        if level > 0:
            data = vars(data)
            streamDict.update({key: data})
            for key, value in data.items():
                if isinstance(value, Namespace):
                    self.namespaceToDict(value, key, level, streamDict)
        else:
            data = vars(data)
            streamDict.update(data)
            for key, value in data.items():
                if isinstance(value, Namespace):
                    self.namespaceToDict(value, key, level, streamDict)

