import os
import subprocess
from sys import exit
import json
from multiprocessing import Process

from os import path, listdir, remove, makedirs
from argparse import Namespace
import warnings
from threading import Thread, Timer
import time

# todo Move away from -b:v and -b:a to b:v:index, etc to enable different bitrates per stream
# todo scaling to height width checking with inHeight/outHeight == inWidth/outWidth and outHeight & outWidth type(int)

# todo ArgArray for vpx (cbr, crf, AND vbr)
# todo Add other audio encoders (lamemp3, fdk-aac, flac)
# todo Print MediaConverter output streams and settings

# todo Longterm
# todo implement ISO-693x for language dictionaries?
# todo MediaStream objects instead of passing around indexes and stuff
# todo MediaConverterQueue (Queueing, progress reports, error handling, etc...)
# todo MediaConverterQueue, skipping, interrupting, sanity checks?, etc...


def split_timecode(time_code):
    """ Takes a timecode string and returns the hours, minutes and seconds. Does not simplify timecode.

    :param time_code: String of format "HH:MM:SS.S" ex. "01:23:45.6"
    :return: HH (float), MM (float), SS (float)
    """
    hh, mm, ss = time_code.split(':')

    hh = float(hh)
    mm = float(mm)
    ss = float(ss)
    return hh, mm, ss


def concat_timecode(HH, MM, SS):
    """ Takes hours, minutes, and seconds, and returns a timecode string in the format of "HH:MM:SS.S".

    :param HH: int, hours
    :param MM: int, minutes
    :param SS: float, seconds
    :return: String of timecode
    """
    seconds = float(SS)
    seconds += 60 * (float(MM) + (float(HH) * 60))

    return seconds_to_timecode(seconds)


def add_timecodes(time_code_1, time_code_2):
    """ Adds to timecodes together and returns the sum of them.

    :param time_code_1: string, timecode
    :param time_code_2: string, timecode
    :return: string, timecode sum
    """
    summation = timecode_to_seconds(time_code_1) + timecode_to_seconds(time_code_2)

    return seconds_to_timecode(summation)


def subtract_timecodes(start_time, end_time):
    """ Subtracts two timecode strings from each other. Returns a timecode. If remaining time is less than one it
        returns '0:00:00.0'

    :param start_time: String of a timecode that will be subtracted from.
    :param end_time: String of a  timecode that will be subtracting.
    :return: String of a timecode that is the remaining time.
    """
    result = timecode_to_seconds(end_time) - timecode_to_seconds(start_time)
    if result < 0:
        result = 0
        print("Warning: The result of subtract_timecodes is less than 0 seconds:")
        print("\twill return '00:00:00' as timecode.")

    return seconds_to_timecode(result)


def timecode_to_seconds(time_code):
    """ Takes a time code and returns the total time in seconds.

    :param time_code: String of a timecode.
    :return: int, seconds equivalent of the timecode
    """
    HH, MM, SS = split_timecode(time_code)

    SS += 60 * (MM + (HH * 60))

    return SS


def seconds_to_timecode(seconds):
    """
    Converts seconds into a conditioned and simplified timecode string
    :param seconds: float, seconds
    :return: string, timecode in 'HH:MM:SS.SSS' format
    """
    h, s = divmod(seconds, 3600)
    m, s = divmod(s, 60)

    s = round(s * 1000)/1000

    hh = str(int(h))
    mm = str(int(m))
    ss = str(s)

    if len(hh) < 2:
        hh = '0' + hh
    if len(mm) < 2:
        mm = '0' + mm

    if ss.find('.') > 1:
        wholes, decimals = ss.split('.')
    else:
        wholes = ss

    if len(wholes) < 2:
        ss = '0' + ss

    return '{0}:{1}:{2}'.format(hh, mm, ss)


def simplify_timecode(time_code):
    """
    Simplifies a timecode to hours: int, minutes: int [0,59], seconds: float(3 decimals) [0, 59.999]
    :param time_code:
    :return:
    """
    return seconds_to_timecode(timecode_to_seconds(time_code))


def get_dir_size(directory_path):
    """
    Gets the size of files in a folder. Non-recursive, ignores folders.
    :param directory_path: string, path of directory to be analyzed
    :return: int, size of sum of files in directory in bytes
    """
    files = [f for f in listdir(directory_path) if path.isfile(path.join(directory_path, f))]
    size = 0
    for file in files:
        size += path.getsize(path.join(directory_path, file))
    return size


def MBtokb(megabytes):
    """ Converts megabytes to kilobits.

    :param megabytes: numeric, megabytes
    :return: numeric, kilobits equivalent.
    """
    kilobytes = megabytes * 8192
    return kilobytes


def renameFile(filepath):
    """ Renames file to file_X.ext where 'X' is a number. Adds '_X' or increments '_X' if already present

    :param filepath: string, the filepath of the file that could be renamed
    :return: string, file name, not a file path
    """
    inDir, fileName = path.split(filepath)

    name, ext = path.splitext(fileName)
    index = name.rfind('_')

    # Check if the characters after the last underscore are just numbers
    if path.isfile(filepath):
        postUnderscore = name[index + 1:]
        for char in postUnderscore:
            # If they aren't, set the counter to 0 and append to file name
            if not char.isdigit():
                name += '_0'
                index = name.rfind('_')
                break

    # Keeps incrementing the number until it creates a new file
    while path.isfile(filepath):
        # split number from name
        number = int(name[index + 1:])
        name = name[:index + 1]

        # increment number, add back to name
        name += str(number + 1)
        fileName = name + ext
        filepath = path.join(inDir, fileName)

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
    listFileName = path.join(str(os.getcwd()), "tempFfConcat.txt")
    with open(listFileName, 'w') as file:
        for items in mediaObjectArray:
            print(str(items.filePath))
            file.write('file ' + "\'" + str(items.filePath) + "\'" + '\n')

    # build "ffmpeg concat" string/array
    # assume all files are same codec/resoultion/params, otherwise ffmpeg will throw it's own error
    ffmpegConcatArr = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', listFileName, '-c', 'copy', outputFilepath]

    # subprocess "ffmpeg concat"
    try:
        processData = subprocess.run(ffmpegConcatArr, check=True)
    except subprocess.CalledProcessError as cpe:
        print("Error: CalledProcess in pympeg.ffConcat()")
        print("CalledProcessError: " + str(cpe))
        processData = None
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
    fileExtensions = ['.mp4', '.mkv', '.avi', '.m4v', '.wmv', '.webm', '.flv', '.mov', '.mpg', '.mpeg', '.ogg', '.ogv',
                      '.ts', '.vob', '.VOB', '.mov', '.MOV', '.rmvb']

    for fileNames in os.listdir(directory):
        if any(extensions in fileNames for extensions in fileExtensions):
            mediaInfo = MediaObject(directory + fileNames)
            mediaInfo.run()
            mediaObjectArray.append(mediaInfo)

    return mediaObjectArray


class MediaConverterQueue:
    def __init__(self, log_directory='', max_processes=1, logging=False, debug=False):
        self.job_list = []
        self.processes = []
        self.refresh_interval = 10  # How often processes are checked to see if they're converted (seconds)
        self.active_processes = 0
        self.start_time = 0
        self.end_time = 0
        self.total_time = 0
        self.done = False

        self.log_directory = log_directory
        self.max_processes = max_processes

    def run(self):
        self.job_list = sorted(self.job_list, key=lambda media: media.mediaObject.fileName)  # todo TEST THIS !!!

        while (self.count_active_processes() < self.max_processes) and (len(self.job_list) > 0):
            self.start_job()
        self.start_time = time.time()

        self.periodic()

    def count_active_processes(self):
        active = 0
        for process in self.processes:
            if process.is_alive():
                active += 1
        return active

    def start_job(self):
        # make sure a job can be started without surpassing self.max_processes!
        if self.count_active_processes() >= self.max_processes:
            print("Failed to start a new job, would exceed maximum processes")
            return

        # make sure there are still jobs to do before popping an empty list!
        if len(self.job_list) < 1:
            print("Failed to start a new job, no more jobs remaining!")
            return

        next_job = self.job_list.pop()
        process = Process(target=next_job.convert, args=())
        process.start()
        self.processes.append(process)

    def prune_dead_processes(self):
        for process in self.processes:
            if (not process.is_alive()) and (type(process) == Process):
                process.terminate()
                ndx = self.processes.index(process)
                del self.processes[ndx]

    def periodic(self):
        self.prune_dead_processes()

        # Check if queue is empty and jobs are done
        if (self.count_active_processes() == 0) and (len(self.job_list) == 0):
            self.done = True
            print("All jobs completed!")
            self.end_time = time.time()
            self.total_time = self.end_time - self.start_time
            print("Took approximately {}.".format(seconds_to_timecode(self.total_time)))
        else:
            while (self.count_active_processes() < self.max_processes) and (len(self.job_list) > 0):
                self.start_job()

            # Schedule next periodic check
            Timer(self.refresh_interval, self.periodic).start()

    def add_job(self, job):
        if type(job) == MediaConverter:
            self.job_list.append(job)
        else:
            print("add_job(job) takes a MediaConverter object, received {}".format(type(job)))
            print("\tQuitting now for safety...")
            exit()

    def add_jobs(self, jobs):
        for job in jobs:
            self.add_job(job)

    def jobs_done(self):
        if len(self.jobList) < 1:
            print("Job's done!")
        else:
            print("Next job is: " + self.jobList[0].fileName)
        pass

    def job_cancelled(self):
        pass

    def write_log(self, logText):
        pass

    def open_log(self):
        pass


class StreamSaver:
    def __init__(self, input_stream, output_file_path_ts):
        self.file_writer = None
        directory, file_name = path.split(output_file_path_ts)

        # make sure output is .ts file for stable writing
        file_name, ext = file_name.split('.')
        file_name += '.ts'

        if not path.isdir(directory):
            os.mkdir(directory)
        if path.isfile(output_file_path_ts):
            file_name = renameFile(file_name)
            output_file_path_ts = path.join(directory, file_name)

        self.args = ['ffmpeg', '-i', str(input_stream), '-c', 'copy', output_file_path_ts]

    def run(self):
        self.file_writer = subprocess.run(self.args)

    def quit(self):
        pass


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
        if not os.path.isdir(outputDirectory):
            os.mkdir(outputDirectory)
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


class MediaObject:
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
        self.resolutions = []
        self.width = 0
        self.height = 0

        # Set by parseMetaInfo()
        self.file_size = path.getsize(self.filePath)
        self.format = {}        # Done
        self.framerates_dec = []
        self.framerates_frac = []
        self.framerate_dec = []
        self.framerate_frac = []
        self.duration = 0       # Done
        self.codecs = []        # Done
        self.streamTypes = []   # Done
        self.videoCodec = ''    # Done
        self.bitrates = []      # Done
        self.video_bitrate = 0  # Done
        self.audio_bitrate = 0  # Done
        self.bitrate = 0        # Done
        self.size = 0           # Done
        self.languages = {}     # todo Add some library matching or something for abbreviations, japan=japanese=jpn=jap etc...

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
            print("Creating MediaObject of: " + str(self.filePath))
            self.ffprobeOut = subprocess.check_output(argsArray).decode("utf-8")
        except subprocess.CalledProcessError as cpe:
            warnings.warn("CalledProcessError with " + self.filePath + " in MediaObject.run()."
                                                                       " File is likely malformed or invalid.")
            print("CalledProcessError: " + str(cpe))
            print()
            self.fileIsValid = False

        if self.fileIsValid:

            self.parseStreams()
            self.parseMetaInfo()


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
            self.videoCodec = [0]
            # warnings.warn("self.videoCodec(): There are more than one video streams present in "
            #               + self.filePath + ", please use self.videoCodecs to view multiple video stream codecs.")
        else:
            try:
                self.videoCodec = vidcodecs[0]
            except IndexError as ie:
                print(ie)
                print("Could not find videoCodec info")


    def parseStreams(self):
        """ Turns the ffprobe json stream output into nested dictionaries stored as a list at self.streams[{}]. Sorts
         streams into seperate lists based on type (audio, video, etc...). Lists of types integers that correspond to
         the index of self.streams[].

        :return:
        """
        ffProbeInfo = json.loads(self.ffprobeOut, object_hook=lambda d: Namespace(**d))

        try:
            # print(self.ffprobeOut)
            self.duration = float(json.loads(self.ffprobeOut)['format']['duration'])

        except KeyError:
            print("Extracting duration from video stream...")
            print("\t"+self.filePath)
            self.duration = timecode_to_seconds(json.loads(self.ffprobeOut)['streams'][0]['tags']['DURATION'])
            print("Extracted duration is {}\n".format(self.duration))

        i = 0
        for stream in ffProbeInfo.streams:
            streamDict = {}
            self.streams.append(streamDict)
            self.namespaceToDict(stream, '', -1, self.streams[i])
            i += 1
        for stream in self.streams:
            if stream['codec_type'] == "video":
                self.videoStreams.append(stream['index'])
                try:
                    self.video_bitrate += int(self.getValueFromKey('bit_rate', stream))
                except TypeError as te:
                    pass
                    # print("File {} does not have a 'bitrate' attribute in video stream. Attempting to infer from audio".format(self.fileName))
                    # print(stream)
                    # print("With file {}".format(self.fileName))

                framerate = self.getValueFromKey('r_frame_rate', stream)
                num, denom = framerate.split('/')
                self.framerates_dec.append(float(num)/float(denom))
                self.framerates_frac.append(framerate)


                # use the larger of coded_dim and dim, select matching dim, add to self.resolutions
                coded_height = int(self.getValueFromKey('coded_height', stream))
                coded_width = int(self.getValueFromKey('coded_width', stream))
                height = int(self.getValueFromKey('height', stream))
                width = int(self.getValueFromKey('width', stream))

                y_dim = max(coded_height, height)
                if y_dim == coded_height:
                    x_dim = coded_width
                else:
                    x_dim = width
                self.resolutions.append((x_dim, y_dim))

            elif stream['codec_type'] == "audio":
                # print("Stream " + str(stream['index']) + " is a audio stream.")
                self.audioStreams.append(stream['index'])
                try:
                    self.audio_bitrate += int(self.getValueFromKey('bit_rate', stream))
                except TypeError as te:
                    pass
                    # print("File {} does not have a 'bitrate' attribute in audio stream. Attempting to infer from audio".format(self.fileName))
                    # print(stream)
                    # print("With file {}".format(self.fileName))

            elif stream['codec_type'] == "subtitle":
                # print("Stream " + str(stream['index']) + " is a subtitle stream.")
                self.subtitleStreams.append(stream['index'])

            elif stream['codec_type'] == "attachment":
                # print("Stream " + str(stream['index']) + " is an attachment stream.")
                self.attachmentStreams.append(stream['index'])

            else:
                # print("Stream " + str(stream['index']) + " is an unrecognized stream.")
                self.unrecognizedStreams.append(stream['index'])


        if self.video_bitrate == 0 and self.audio_bitrate == 0:
            self.audio_bitrate = 128000
            # print("Can't infer either video or audio bitrates."
            #       " Assuming audio bitrate of {} kb/s to infer video bitrate".format(self.audio_bitrate/1000))

            self.video_bitrate = (8 * self.file_size - self.audio_bitrate * self.duration) / self.duration

        elif self.video_bitrate == 0:
            # print("Infering video bitrate from audio bitrate...")
            self.video_bitrate = (8 * self.file_size - self.audio_bitrate * self.duration) / self.duration

        elif self.audio_bitrate == 0:
            # print("Infering audio bitrate from video bitrate...")
            self.audio_bitrate = (8 * self.file_size - self.video_bitrate * self.duration) / self.duration

        # choosing default self.width and self.height from multiple streams, always pick the largest and matching
        if len(self.videoStreams) != 0:
            widths = []

            for ndx in range(len(self.resolutions)):
                widths.append(self.resolutions[ndx][0])

            self.width = max(widths)
            primary_vid_stream = widths.index(self.width)
            self.height = self.resolutions[primary_vid_stream][1]
            self.framerate_dec = self.framerates_dec[primary_vid_stream]
            self.framerate_frac = self.framerates_frac[primary_vid_stream]


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

