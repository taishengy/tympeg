"""Converts media files in specified sub directories of parent_dir to x265 video and opus audio. Keeps only the
first video and audio stream found.Doesn't attempt to retain subtitles or attachment streams. Attempts to
calculate the bits/pixel of each file and uses a user specified crf quality for bits/pixel intervals, otherwise
uses a user specified default CRF and audio bitrate & channel setup. Prints helpful stats and can save a log
file to each sub directory."""

import datetime
import os
import sys
import time

from tympeg import MediaConverter, makeMediaObjectsInDirectory, calc_bits_per_pixel, split_ext, get_dir_size

# This will convert all files in /media/folder1 and /media/folder2 (non-recursive) and will place a log file in each folder
# parent_dir = '/media/'
# dirs_to_convert = ['folder1', 'folder2']

speed = 'veryfast'  # Reminder: this is x265, don't expect x264 speeds
log_file = True

# Quality intervals for quality dicts: X & Y are bits/pixel thresholds; a, b, & c are crfs corresponding to intervals
# Bits/pixel       X           Y
# <----------------](----------](----------->
# CRF     a              b             c
# Upper bounds are always inclusive, lower bounds are exclusive
# Some example quality dicts. They can be any number of intervals, but threshold[0] == 0, and each entry
# except 'default' must be equal lengths. see save_bits_per_pixel_dist() in tools.py for help visualizing bits/pixel
# distribution for defining your own intervals

s = 'stereo'
m = 'mono'

qualities_HQ = {  # HQ
    'threshold': [0, 0.08, 0.11],
    'video': [25, 23, 20],
    'audio': [(64, m), (96, m), (128, s)],
    'default': [23, (96, s)]}  # default to stereo here 96k

qualities_LQ = {
    'threshold': [0, 0.10, 0.14],
    'video': [27, 25, 23],
    'audio': [(64, m), (82, m), (96, m)],
    'default': [23, (96, s)]}

qualities_HQ_high_min = {
    'threshold': [0, 0.08, 0.11],
    'video': [23, 21, 20],
    'audio': [(96, s), (96, s), (128, s)],
    'default': [23, (96, s)]}  # default to stereo here 96k

qualities = qualities_HQ_high_min


class PrintLogger:
    """
    Simple class that can write and print the same string.
    """
    def __init__(self, log_file_path, logging):
        self.log_file_path = log_file_path
        self.logging = logging
        
    def pl(self, st):
        print(st)
        if self.logging:
            with open(self.log_file_path, 'a', encoding='utf8') as log:
                log.write(st + "\n")
            log.close()


def convert_folder_x265(dir_path, qualities, speed, autodelete=False, log=True):
    """
    Does the converting of sub directories. A lot of the stuff in here is for reporting stats back to user/log.
    :param dir_path: string, path to directory
    :param qualities: dict, qualities dict, see note at top of file
    :param speed: str, x265 speed parameter
    :param autodelete: bool, sets if original files should be deleted after conversion
    :param log: bool, True writes log file into directory, False doesn't
    :return:
    """


    # declare some media arguments
    codec = 'x265'

    # start the log
    sep = "{:-^60}".format('--')
    now = datetime.datetime.now()
    log_file_name = 'converter_log.txt'
    log_file_path = os.path.join(dir_path, log_file_name)
    lo = PrintLogger(log_file_path, log)
    lo.pl("Log of \"{}\" conversion".format(dir_path))
    lo.pl("Run on:     {}".format(now.strftime("%Y %b %d")))
    lo.pl("Started at: {}".format(now.strftime("%I:%M:%S %p")))
    lo.pl(sep)

    # Figure out what files need to be converted to h265
    all_files = makeMediaObjectsInDirectory(dir_path)
    files_to_move = []
    for media in all_files:
        if media.videoCodec != 'hevc':
            files_to_move.append(media)

    # move files
    original_files_dir = os.path.join(dir_path, 'original_files')

    # if len(files_to_move) == 0:
    #     print("\n\nNo files to convert in {}, breaking...\n\n".format(dir_path))
    #     return

    if not os.path.isdir(original_files_dir):
        os.mkdir(original_files_dir)
    for media in files_to_move:
        try:
            os.rename(media.filePath, os.path.join(original_files_dir, media.fileName))
        except FileExistsError:
            lo.pl("\nFile: {}\n\tAlready exists! Skipping this one...".format(media.filePath))
            continue

    # convert files
    files_to_convert = makeMediaObjectsInDirectory(original_files_dir)
    # print(original_files_dir)
    # print(files_to_convert)
    output_file_size = 0
    input_file_size = 0
    count = 1
    time_start = time.time()
    total_files = len(files_to_convert)
    total_input_size = get_dir_size(original_files_dir)/1000000
    for media in files_to_convert:
        video_rate, audio_rate, channels = decide_quality(qualities, media)
        name, ext = split_ext(media.fileName)
        output_file_path = os.path.join(dir_path, name + '.mkv')
        media_size = media.file_size/1000000  # MB
        now = datetime.datetime.now()

        lo.pl("\nBeginning to convert file {} of {}:".format(count, total_files))
        lo.pl("\t{}".format(media.fileName))
        lo.pl("\tFile is {:0,.2f} MB".format(media_size))
        lo.pl("\tFile bits/pixel: {:0,.4f}".format(calc_bits_per_pixel(media)))
        lo.pl("\tVideo quality of {} and audio rate of {} kb/s".format(video_rate, audio_rate))
        lo.pl("\tStarted at {}\n".format(now.strftime("%I:%M:%S %p")))
        if os.path.isfile(output_file_path):
            lo.pl("Output file already exists!!! Skipping...")
            lo.pl("{:{align}{width}}".format("-------   DONE   -------", align='^', width=len(sep)))
            count += 1
            total_input_size -= media_size
            continue
        lo.pl("...converting...")
        print("Using profile")

        cvt = MediaConverter(media, output_file_path)
        audio = True
        video = True

        try:
            cvt.createVideoStream(codec, 'crf', video_rate, speed)
        except IndexError:
            lo.pl("NO VIDEO FOUND")
            video = False
        try:
            cvt.createAudioStream(media.audioStreams[0], 'opus', audioBitrate=audio_rate, audioChannels=channels)
        except IndexError:
            lo.pl("NO AUDIO FOUND")
            audio = False

        if not audio and not video:
            print("\nNo audio or video found, skipping...")
            continue

        sec = cvt.convert()
        end = time.time()

        output_file_size += os.path.getsize(output_file_path)/1000000
        input_file_size += media_size
        minutes = sec/60
        input_rate = media_size/minutes
        avg_rate = input_file_size/((end - time_start)/60)
        eta_hours, eta_min = divmod(round((total_input_size - input_file_size)/avg_rate, 0), 60)

        if autodelete:
            os.remove(media.filePath)

        lo.pl('\nCompleted file {0} of {1} at {2} in {3:,.2f} min'.format(count, total_files,
                                                                          now.strftime("%I:%M:%S %p"), minutes))
        lo.pl('Completed file at input rate of: {0:,.2f} MB/min'.format(input_rate))
        lo.pl('Average rate of: {0:,.2f} MB/min so far'.format(avg_rate))
        lo.pl('Estimated time for remaining files: {0}:{1}'.format(int(eta_hours), int(eta_min)))
        lo.pl('Total input converted: {0:,.2f} MB of {1:,.2f} MB'.format(input_file_size, total_input_size))
        lo.pl('Total output size: {0:,.2f} MB'.format(output_file_size))
        lo.pl('Output/Input ratio: {0:,.3f}\n'.format(output_file_size/input_file_size))
        lo.pl(sep)

        count += 1

    if autodelete:
        try:
            os.rmdir(original_files_dir)
        except OSError:
            print("{} could not be removed. Most likely because a file wasn't converted because "
                  "it already exists in the parent directory and the original file is present "
                  "for your review.")

    lo.pl("{:{align}{width}}".format("-------   DONE   -------", align='^', width=len(sep)))


def decide_quality(qualities, media_object):
    """Chooses the crf quality of the video as well as the bitrate and channels of the audio files from the
    supplied qualities dict.

    :param qualities: dict, see notes at top of file
    :param media_object: MediaObject
    :return: Int, crf level
             Int or Float, audio bitrate
             Int, audio channels
    """
    q = qualities
    bits_pixel = calc_bits_per_pixel(media_object)

    # Making sure qualities is valid
    n = len(q['threshold'])
    if (len(q['video']) != n) or (len(q['audio']) != n):
        print("\n\nYour qualities variable isn't set up correctly!")
        print("'threshold', 'video', and audio values need to have equal length.")
        print("Additionally, 'threshold'[0] needs to be 0")
        print("Exiting...")
        sys.exit()

    # Set defaults up front
    crf = q['default'][0]
    audio_bitrate = q['default'][1][0]
    audio_channels = q['default'][1][1]

    if bits_pixel <= 0:  # Print warning if it looks like defaults will be used
        print("Unable to calculate bits per pixel, defaulting to: "
              "crf = {}, audio = {}k, channels = {}".format(crf, audio_bitrate, audio_channels))

    for x in range(0, n):
        if bits_pixel > q['threshold'][x]:
            crf = q['video'][x]
            audio_bitrate = q['audio'][x][0]
            audio_channels = q['audio'][x][1]

    return crf, audio_bitrate, audio_channels

