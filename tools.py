from pympeg import *
import time


def listdirs(path):
    dirs = []
    for item in os.listdir(path):
        if os.path.isdir(os.path.join(path, item)):
            dirs.append(os.path.join(path, item))
    return dirs


def alphaConcatFilesInDirectory(inputDirPath, alphabetical=True):
    """
    Attempts to concat ALL files in a directory, be careful!
    :return:
    """
    mediaObjectArray = makeMediaObjectsInDirectory(inputDirPath)
    if alphabetical == True:
        mediaObjectArray = sorted(mediaObjectArray, key=lambda media: media.fileName)
    outputPath, tail = path.split(inputDirPath)
    ffConcat(mediaObjectArray, path.join(outputPath, mediaObjectArray[0].fileName))

def quickClip(filepath, startTime, endTime, outputPath=''):
    media = MediaObject(filepath)
    cvt = MediaConverter(media, outputPath)

    for videoIndex in media.videoStreams:
        cvt.createVideoStream('copy', 'copy', 0, videoStream=videoIndex)

    for audioIndex in media.audioStreams:
        cvt.createAudioStream(audioEncoder='copy', audioStream=audioIndex)

    cvt.createSubtitleStreams(media.subtitleStreams)
    cvt.clip(startTime, endTime)

def convertFilesThatArentVideoCodec(inputFolder, videoCodec, videoEncoder, rateControlMethod, videoRate, speed,
                                    audioEncoder, audioBitrate, channels):
    """ Searches directory for videos NOT encoded with videoCodec, moves them to a seperate file and encodes them
     to the selected codec, saving the encodes in the original directory. Retains all streams.

    :param inputFolder: string, the folder to be searched and converted
    :param videoCodec: string, video Codec to search for 'hevc' for h265 video
    :param videoEncoder: string, video encoder ffmpeg should use ('x265', 'x264', 'vp8', 'vp9')
    :param rateControlMethod: string, rate control method ('crf', 'cbr', 'vbr)
    :param videoRate: int, rate of video. Either quality factor or bitrate
    :param speed: string, speed of x26X family encoders
    :param audioEncoder: string, audio encoder ('opus', 'aac', 'fdk', etc...)
    :param audioBitrate: int, bitrate of audio
    :param channels: string, channel layout of audio ('mono', 'stereo')
    :return:
    """

    # create original folder if it doesn't exist
    originalFilesDir = path.join(inputFolder, "original_files/")

    if not path.isdir(originalFilesDir):
        os.mkdir(originalFilesDir)

    # figure out what isn't the codec and move those to originalFilesDir
    sortingMediaArray = makeMediaObjectsInDirectory(inputFolder)

    for media in sortingMediaArray:
        if media.videoCodec != str(videoCodec):
            # print("Files moved to: " + str(path.join(originalFilesDir, str(media.fileName))))
            os.rename(path.join(inputFolder, str(media.fileName)), path.join(originalFilesDir, str(media.fileName)))

    # convert files in original_files folder
    convertingMediaArray = makeMediaObjectsInDirectory(originalFilesDir)
    totalFiles = str(len(convertingMediaArray))
    print("\n\nConverting " + totalFiles + " files...\n\n")

    count = 0
    inputFileSize = 0
    outputFileSize = 0
    timeStart = time.time()
    totalInputSize = getDirSize(originalFilesDir)/1000000

    for media in convertingMediaArray:
        name, ext = path.splitext(media.fileName)
        outputFilePath = path.join(inputFolder, name + '.mkv')
        cvt = MediaConverter(media, outputFilePath)

        cvt.createVideoStream(videoEncoder, rateControlMethod, videoRate, speed)

        for audioStream in range(0, len(media.audioStreams)):
            cvt.createAudioStream(media.audioStreams[audioStream], audioEncoder, audioBitrate, audioChannels=channels)

        cvt.createSubtitleStreams(media.subtitleStreams)
        count += 1
        print("Converting file " + str(count) + ' of ' + totalFiles + ":")
        print("\t{0} ({1} MB)\n".format(media.filePath), path.getsize(originalFilesDir + media.fileName)/1000000)

        start = time.time()
        cvt.convert()
        end = time.time()

        outputFileSize += path.getsize(outputFilePath)/1000000
        inputFileSize += path.getsize(originalFilesDir + media.fileName)/1000000
        minutes = (end - start)/60
        inputRate = (path.getsize(originalFilesDir + media.fileName)/1000000)/minutes
        avgRate = inputFileSize/((end - timeStart)/60)
        etaH, etaM = divmod(round((totalInputSize - inputFileSize)/avgRate, 0), 60)

        print('\nCompleted file {0} of {1} in {2} min'.format(count, totalFiles, minutes))
        print('Completed file at input rate of: {0:2f} MB/min'.format(inputRate))
        print('Average rate of: {0:2f} MB/min'.format(avgRate))
        print('ETA: {0}:{1}'.format(etaH, etaM))
        print('Total input converted: {0:2f} MB of {1:2f} MB'.format(inputFileSize, totalInputSize))
        print('Total output size: {0:2f} MB'.format(outputFileSize))
        print('Output/Input ratio: {0:3f}'.format(outputFileSize/inputFileSize))
        print("\n\n")

    timeEnd = time.time()
    totalSeconds = timeEnd - timeStart
    m, s = divmod(totalSeconds, 60)
    minutes = m
    h, m = divmod(m, 60)
    print("Total operation completed in: %d:%02d:%02d" % (h, m, s))
    print("Total size of files converted: " + str(inputFileSize) + " MB => " + str(outputFileSize) + " MB")
    print("Average rate of input converted: " + str((inputFileSize/minutes)) + " MB/min")

def convertFolderx265Profile(inputFolder, profile):
    videoEncoder = 'x265'
    rateControlM = 'crf'
    audioEncoder = 'opus'

    if profile == 'low':
        rate = 25
        speed = 'veryfast'

        audioBitrate = 48
        channels = 'mono'

    elif profile == 'medium':
        rate = 23
        speed = 'veryfast'

        audioBitrate = 96
        channels = 'stereo'

    elif profile == 'high':
        rate = 20
        speed = 'veryfast'

        audioBitrate = 128
        channels = 'stereo'

    else:
        print("Profile specified not valid. Specify 'high', 'medium' or 'low'.")
        return

    convertFilesThatArentVideoCodec(inputFolder, 'hevc', videoEncoder, rateControlM, rate, speed,
                                    audioEncoder, audioBitrate, channels)

def concatFilesGroupedByFolders(parentDir):
    dirs = listdirs(parentDir)
    for dir in dirs:
        print(dir)
        alphaConcatFilesInDirectory(dir)