from tympeg.util import renameFile
import subprocess
import time
import warnings
from os import path, mkdir

from .timecode import timecode_to_seconds, seconds_to_timecode, subtract_timecodes

from .util import renameFile


class MediaConverter:
    """ Holds settings that get turned into an arg array for ffmpeg conversion
    """
    def __init__(self, mediaObject, outputFilePath='', debug=False, verbosity=24):
        """ Generates a ConversionSettings object. Populate fields with createXSettings() Methods.

        :param mediaObject:  MediaObject of file to be created
        :param outputFilePath: string, file path of output file
        :param debug: bool, whether or not to print certain messages helpful with debugging
        :param verbosity: int, level of ffmpeg verbosity. Integers correspond to ffmpeg's -loglevel options
        :return:
        """
        # general conversion settings
        self.mediaObject = mediaObject
        self.debug = debug
        self.verbosity = verbosity

        # parse MediaObject if it hasn't been done
        if self.mediaObject.streams == []:
            self.mediaObject.run()

        try:
            self.inputFilePath = self.mediaObject.format['filename']
        except KeyError:
            self.inputFilePath = self.mediaObject.filePath
            print("Filename not found in format dictionary for file {}".format(self.mediaObject.fileName))
            print()
        self.inputFileName = path.basename(self.inputFilePath)
        inDir, inFileName = path.split(self.mediaObject.filePath)
        outDir, outFileName = path.split(outputFilePath)

        #renaming logic
        if outputFilePath == '':
            outputFilePath = path.join(inDir, renameFile(self.mediaObject.filePath))

        else:  # if path.isfile(outputFilePath):
            outFileName = renameFile(path.join(outDir, outFileName))
            outputFilePath = path.join(outDir, outFileName)

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
        if not path.isdir(outputDirectory):
            mkdir(outputDirectory)
        startTime= time.time()
        subprocess.run(self.argsArray)
        endTime = time.time()
        return endTime - startTime

    def clip(self, startingTime, endingTime):
        self.generateArgsArray(startTime=startingTime, endTime=endingTime)
        print(self.argsArray)

        self.convert()

    def createVideoStream(self, videoEncoder, rateControlMethod, rateParam, speed='',
                          width=-1, height=-1, videoStream=-1):
        """

        :param videoEncoder: string, encoder used. Currently 'x264', 'x265', 'vpx', 'copy' are supported
        :param rateControlMethod: string, rate control method to be used by the encoder
        :param rateParam: int, interpreted as bitrate or constant rate factor, depending on rateControlMethod
        :param speed: string, speed used to encode video in x26X family of encoders
        :param width: int, width to scale to
        :param height: int, height to scale to
        :param videoStream: int, manually specify a stream if mediaObject has multiple video streams.
        :return:
        """

        # todo allow encoding multiple videostreams at different resolutions/rates/modes/codecs
        # todo implement lossless=True, changes lots of stuff up

        def buildvpXStream(videoSettingsDict, rateControlMethod, rateConstant):
            """

            :param rateControlMethod: string, vbr, cbr, crf
            :param rateConstant: int, either a bitrate (vbr, cbr), or a rate constant (crf)
            :return:
            """
            # cbr or crf, set values
            if rateControlMethod == 'cbr':
                videoSettingsDict.update({'bitrateMode': rateControlMethod})

                if rateConstant == -1:
                    raise ValueError("No desired bitrate specified with constant bitrate encoding selected. Please"
                                     " specify a bitrate in createVideoSetting(... rateConstant= ...)")

                if isinstance(rateConstant, float):
                    rateConstant = int(round(rateConstant))

                elif not isinstance(rateConstant, int):
                    raise ValueError("'rateConstant' parameter not understood. Desired bitrate should be float or int in kbit/s.")

                videoSettingsDict.update({'rateConstant': rateConstant})

            elif rateControlMethod == 'vbr':
                videoSettingsDict.update({'bitrateMode': rateControlMethod})

                if rateConstant == -1:
                    raise ValueError("No desired bitrate specified with constant rate factor encoding selected. Please"
                                     " specify a rate factor with createVideoSetting(... rateConstant= ...)")

                if isinstance(rateConstant, float):
                    rateConstant = int(round(rateConstant))

                elif not isinstance(rateConstant, int):
                    raise ValueError("'rateConstant' parameter not understood. Desired bitrate should be float or int in kbit/s.")

                videoSettingsDict.update({'rateConstant': rateConstant})

            elif rateControlMethod == 'crf':
                videoSettingsDict.update({'bitrateMode': rateControlMethod})

                if rateConstant == -1:
                    raise ValueError("No desired rate factor specified with constant rate factor encoding selected. Please"
                                     " specify a rate factor with createVideoSetting(... rateConstant= ...)")

                if not (isinstance(rateConstant, float) or isinstance(rateConstant, int)) or rateConstant < 0 or rateConstant > 63:
                    raise ValueError("'rateConstant' parameter not understood. Constant Rate Factor must "
                                     "be an integer between 4 and 63")

                if isinstance(rateConstant, float):
                    rateConstant = int(round(rateConstant))

                videoSettingsDict.update({'rateConstant': rateConstant})

            else:
                raise ValueError("No rate control method indicated. Please specify"
                                 " createVideoStream(bitRateMode= rateConstant OR rateConstant) and a rate control target")

        def buildx26XStream(videoSettingsDict, rateControlMethod, rateConstant, speed):
            """

            :param rateControlMethod: string, cbr, crf
            :param rateConstant: int, either a bitrate (cbr), or a rate constant (crf)
            :return:
            """

            # cbr or crf, set values
            if rateControlMethod == 'cbr':
                videoSettingsDict.update({'bitrateMode': rateControlMethod})

                if rateConstant == -1:
                    raise ValueError("No desired bitrate specified with constant bitrate encoding selected. Please"
                                     " specify a bitrate in createVideoSetting(... rateConstant= ...)")

                if isinstance(rateConstant, float):
                    rateConstant = int(round(rateConstant))

                elif not isinstance(rateConstant, int):
                    raise ValueError("'rateConstant' parameter not understood. Desired bitrate should be float or int.")

                videoSettingsDict.update({'rateConstant': rateConstant})

            elif rateControlMethod == 'crf':
                videoSettingsDict.update({'bitrateMode': rateControlMethod})

                if rateConstant == -1:
                    raise ValueError("No desired rate factor specified with constant rate factor encoding selected. Please"
                                     " specify a rate factor with createVideoSetting(... rateConstant= ...)")

                if not (isinstance(rateConstant, float) or isinstance(rateConstant, int)) or rateConstant < 0 or rateConstant > 51:
                    raise ValueError("'rateConstant' parameter not understood. Constant Rate Factor must "
                                     "be an integer between 0 and 51")

                if isinstance(rateConstant, float):
                    rateConstant = int(round(rateConstant))

                videoSettingsDict.update({'rateConstant': rateConstant})

            else:
                raise ValueError("No rate control method indicated. Please specify"
                                 " createVideoStream(bitRateMode= rateConstant OR rateConstant) and a rate control target")

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

        def buildCopyStream(videosSettingsDict):
            """

            :param rateControlMethod: string, vbr, cbr, crf
            :param rateConstant: int, either a bitrate (vbr, cbr), or a rate constant (crf)
            :return:
            """
            videoSettingsDict.update({'videoEncoder': 'copy'})

        videoSettingsDict = {}

        # Video Stream selection
        # default to first videoStream in file
        if videoStream == -1:
            videoStream = self.mediaObject.videoStreams[0]

        # Verify that stream contains video
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

        supportedEncoders = ['x264', 'x265', 'vp8', 'vp9', 'copy'] # todo test three encoders

        if videoEncoder in supportedEncoders:
            videoSettingsDict.update({'videoEncoder': videoEncoder})
        else:
            ValueError(videoEncoder + " is not supported. Currently supported encoders are: " + str(supportedEncoders))

        if (videoEncoder == 'x264') or (videoEncoder == 'x265'):  # simplified or's didn't work 100%?
            buildx26XStream(videoSettingsDict, rateControlMethod, rateParam, speed)
        elif (videoEncoder == 'vp8') or (videoEncoder == 'vp9'):
            buildvpXStream(videoSettingsDict, rateControlMethod, rateParam)
        elif videoEncoder == 'copy':
            buildCopyStream(videoSettingsDict)
        else:
            print("Video encoder parameter not understood in MediaConverter.createVideoStream().")
            print("Supported encoder parameters are: " + str(supportedEncoders))

        # Set resolution from parameter, default same resolution as source
        if videoEncoder == 'copy':
            videoSettingsDict.update({'width': -1})
            videoSettingsDict.update({'height': -1})
        else:  # Set by parameters
            videoSettingsDict.update({'width': int(width)})
            videoSettingsDict.update({'height': int(height)})

            if self.debug:
                if (height == -1 or width != -1) or (height != -1 or width == -1):
                    if height == -1:
                        print("Scaling to width of " + str(width) + " pixels.")
                    else:
                        print("Scaling to height of " + str(height) + " pixels.")
                else:
                    print("Scaling to width of " + str(width) + " and height of " + str(height) + " pixels.")

        videoSettingsDict.update({'index': int(videoStream)})
        self.videoStreams.append(videoSettingsDict)

        if self.debug:
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

                # if str(stream['bitrateMode']) == 'cbr':
                #     print('self.cbr: ' + str(stream['cbr']) + " kbits/s")
                # elif str(stream['bitrateMode']) == 'crf':
                #     print('self.crf: ' + str(stream['crf']))

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
        supportedAudioEncoders = ['aac', 'opus', 'vorbis', 'copy'] # todo test three encoders

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

        audioSettingsDict.update({'index': int(audioStream)})
        self.audioStreams.append(audioSettingsDict)
        # self.printAudioSetting()

    def printAudioSetting(self):
        """ Prints the audio settings of the ConversionSettings object.

        :return:
        """
        streamIndex = 0
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


        for streams in subtitleStreams:
            subtitleSettings = {}
            subtitleSettings.update({'index': int(streams)})
            self.subtitleStreams.append(subtitleSettings)


    def generateArgsArray(self, startTime='0', endTime='0'):
        """ Generates the argArray to feed ffmpeg. Generates from the output stream information provided in the
            self.createXstream() methods.

        :param startTime: String, input start time for encoding in format HH:MM:SS.SS
        :param endTime: String, input end time for encoding in format HH:MM:SS.SS
        :return:
        """
        def mapStreamsByType(someStreams, fileIndex, argsArray):
            """ Writes the -map stream to the argArray. Look at how it's called below.

            :param someStreams:
            :param fileIndex:
            :param argsArray:
            :return:
            """
            for stream in someStreams:
                argsArray.append('-map')
                argsArray.append(fileIndex + str(stream['index']))


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
            """
            Calculates the timecodes to fast-seek (jumps to nearest key-frame past this timecode) start/stop timecodes
            :param startTime: Timecode of where the video should be fully decoded
            :param endTime: Timecode of when to stop decoding/transcoding
            :return: fastSeekTime, startTime, endTime, all timecodes
            """
            slow_seek_gap = 90 # gap in seconds between when fastseek stops and video is fully decoded to startTime
            if timecode_to_seconds(startTime) < slow_seek_gap + 15:
                fastSeekTime = '00:00:00'
            else:
                fastSeekTime = subtract_timecodes(seconds_to_timecode(slow_seek_gap), startTime)
            startTime = subtract_timecodes(fastSeekTime, startTime)
            endTime = subtract_timecodes(fastSeekTime, endTime)

            if self.debug:
                print("Fast Seeking To: " + fastSeekTime + " from " + startTime)
                print("Encoding from " + startTime + " to " + endTime + " after fastSeeking.")
                print("Encoding " + subtract_timecodes(startTime, endTime) + " of media.")
            return fastSeekTime, startTime, endTime

        streamCopy = False
        cut = False

        addArgsToArray('-v ' + str(self.verbosity), self.argsArray)

        if (startTime != '0') and (endTime != '0'):
            cut = True

            fastSeekTime, startTime, endTime = fastSeek(startTime, endTime)
            addArgsToArray('-ss ' + fastSeekTime, self.argsArray)
            addArgsToArray('-i ', self.argsArray)
            self.argsArray.append(str(self.mediaObject.filePath))

            # self.argsArray.append()
            addArgsToArray('-ss ' + startTime, self.argsArray)
            addArgsToArray('-to ' + endTime, self.argsArray)

        else:
            addArgsToArray('-i', self.argsArray)
            self.argsArray.append(str(self.mediaObject.filePath))


        fileIndex = '0:'

        # -map each stream
        for streamType in [self.videoStreams, self.audioStreams, self.subtitleStreams, self.attachmentStreams, self.otherStreams]:
            mapStreamsByType(streamType, fileIndex, self.argsArray)

        if self.debug:
            print("Conversion argArray after stream mapping: " + str(self.argsArray))

        # Video Streams and their args
        vidStrings = []
        ffVideoEncoderNames = {'x264': 'libx264',
                               'x265': 'libx265',
                               'vp8': 'libvpx',
                               'vp9': 'libvpx-vp9',
                               'copy': 'copy'}

        for stream in self.videoStreams:
            streamIndex = 0
            if stream['videoEncoder'] == 'copy':
                streamCopy = True
                addArgsToArray('-c:v copy', self.argsArray)
                vidStrings.append('-c:v copy')

            else:
                vidString = ' -c:v ' + ffVideoEncoderNames[stream['videoEncoder']]

                if stream['bitrateMode'] == 'cbr':
                    if stream['videoEncoder'] == 'vp9' or 'vp8':
                        vidString += ' -minrate ' + str(stream['rateConstant']) + 'k' + ' -maxrate ' \
                                     + str(stream['rateConstant']) + 'k' + ' -b:v ' + str(stream['rateConstant']) + 'k'
                    else:
                        vidString += ' -b:v ' + str(stream['rateConstant']) + 'k'
                elif stream['bitrateMode'] == 'crf':
                    if stream['videoEncoder'] == 'vp9':
                        vidString += ' -crf ' + str(stream['rateConstant']) + ' -b:v 0 '
                    else:
                        vidString += ' -crf ' + str(stream['rateConstant'])

                elif stream['bitrateMode'] == 'vbr':  # todo Check out ffmpeg's vp8/vp9 encoding guide, add that stuff
                    vidString += ' -b:v ' + str(stream['rateConstant']) + 'k'
                else:
                    warnings.warn("'bitrateMode' not understood in generateArgsArray. Should be 'cbr', 'vbr', 'crf'.")

                vidString += ' -vf scale=' + str(stream['width']) + ":" + str(stream['height'])

                if stream['videoEncoder'] == 'x264' or stream['videoEncoder'] == 'x265':
                    vidString += ' -preset ' + str(stream['speed'])

                addArgsToArray(vidString, self.argsArray)
                vidStrings.append(vidString)

            streamIndex += 1
            # print('Video stream ' + str(stream['videoStream']) + ' ffmpeg arguments:' + str(vidStrings[-1]))

        if self.debug:
            print("Conversion argArray after video stream(s): " + str(self.argsArray))

        # Audio Streams and their args
        audioStrings = []
        ffAudioEncoderNames = {'aac': 'aac',
                               'fdk': 'libaac_fdk',
                               'lame': 'libmp3lame',
                               'flac': 'flac',
                               'opus': 'libopus',
                               'vorbis': 'libvorbis',
                               'copy': 'copy'}

        streamIndex = 0
        for stream in self.audioStreams:
            if stream['audioEncoder'] == 'copy':
                streamCopy = True
                fragment = ' -c:a:' + str(streamIndex) + ' copy'
                addArgsToArray(fragment, self.argsArray)
                audioStrings.append(fragment)

            elif stream['audioEncoder'] == 'opus':
                if stream['audioChannels'] == 'mono':
                    # todo opus mono! https://trac.ffmpeg.org/ticket/5718
                    addArgsToArray('-c:a:' + str(streamIndex) + ' ' + str(ffAudioEncoderNames[stream['audioEncoder']]) +
                                   " -af aformat=channel_layouts=mono", self.argsArray)

                    addArgsToArray('-b:a:' + str(streamIndex) + ' ' + str(stream['audioBitrate']) + 'k ', self.argsArray)
                    if stream['audioBitrate'] != 128:
                        addArgsToArray('-vbr constrained', self.argsArray)

                else: # opus stereo
                    addArgsToArray('-c:a:' + str(streamIndex) + ' ' + str(ffAudioEncoderNames[stream['audioEncoder']]), self.argsArray)

                    addArgsToArray('-b:a:' + str(streamIndex) + ' ' + str(stream['audioBitrate']) + 'k ', self.argsArray)
                    if stream['audioBitrate'] != 128:
                        addArgsToArray('-vbr constrained', self.argsArray)
            # elif stream['audioEncoder'] == 'fdk':
            #     if stream['audioChannels'] == 'mono':
            #
            #     else:
            #         addArgsToArray('-c:a:{} {} -profile=aac_low'.format(streamIndex, ffAudioEncoderNames[stream['audioEncoder']]), self.argsArray)
            else:
                addArgsToArray('-c:a:' + str(streamIndex) + ' ' + str(ffAudioEncoderNames[stream['audioEncoder']]), self.argsArray)
                addArgsToArray('-b:a:' + str(streamIndex) + ' ' + str(stream['audioBitrate']) + 'k ', self.argsArray)

            streamIndex += 1

        if self.debug:
            print("Conversion argArray after audio stream(s): " + str(self.argsArray))

        for stream in self.subtitleStreams:
            # if self.mediaObject.subtitleStreamTypes[stream]
            addArgsToArray('-c:s copy', self.argsArray)

        if self.debug:
            print("Conversion argArray after subtitle stream(s): " + str(self.argsArray))

        if streamCopy and cut:
            addArgsToArray('-avoid_negative_ts 1', self.argsArray)
        self.argsArray.append(self.outputFilePath)

        if self.debug:
            print("Conversion argArray after output file: " + str(self.argsArray))

    def estimateVideoBitrate(self, targetFileSize, startTime=-1, endTime=-1, audioBitrate=-1, otherBitrates=0):

        if startTime == -1 and endTime == -1:
            duration = timecode_to_seconds(self.mediaObject.duration)
        else:
            duration = timecode_to_seconds(subtract_timecodes(startTime, endTime))

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
