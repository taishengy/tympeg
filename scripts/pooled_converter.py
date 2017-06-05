"""A pooled converter that behaves in very similar ways to convert_sub_dirs.py. Lower logging and stat print outs than
convert_sub_dirs.py. Useful for batch converting lower resolution video files that can't fully use all cores. """

import os
from os import path
import sys

from tools import calc_bits_per_pixel, split_ext
from pympeg import makeMediaObjectsInDirectory, MediaConverter, MediaConverterQueue, seconds_to_timecode
import time

"""Converts media files in specified sub directories of parent_dir to x265 video and opus audio. Keeps only the
first video and audio stream found.Doesn't attempt to retain subtitles or attachment streams. Attempts to
calculate the bits/pixel of each file and uses a user specified crf quality for bits/pixel intervals, otherwise
uses a user specified default CRF and audio bitrate & channel setup. Prints helpful stats and can save a log
file to each sub directory."""

parent_dir = '/media/television/'
dirs_to_convert = ['folder1', 'folder2']
speed = 'superfast'  # Reminder: this is x265, don't expect x264 speeds
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

qualities = qualities_HQ

class PrintLogger:
    def __init__(self, log_file_path, logging):
        self.log_file_path = log_file_path
        self.logging = logging

    def pl(self, s):
        print(s)
        if self.logging:
            with open(self.log_file_path, 'a', encoding='utf8') as log:
                log.write(s + "\n")
            log.close()


def convert_folder_x265(dir_path, log=True):
    # declare some media arguments
    concurrency = 2
    speed = 'veryfast'
    codec = 'x265'

    # Figure out what files need to be converted to h265
    all_files = makeMediaObjectsInDirectory(dir_path)
    files_to_move = []
    for media in all_files:
        if media.videoCodec != 'hevc':
            files_to_move.append(media)

    # move files
    original_files_dir = path.join(dir_path, 'original_files')

    for media in files_to_move:
        if not path.isdir(original_files_dir):
            os.mkdir(original_files_dir)
        try:
            os.rename(media.filePath, path.join(original_files_dir, media.fileName))
        except FileExistsError:
            print("\nFile: {}\n\tAlready exists! Skipping this one...".format(media.filePath))
            continue

    # Build MediaConverter object array
    files_to_convert = makeMediaObjectsInDirectory(original_files_dir)
    c = []
    accum_input_size = 1  # 1 byte to avoid div by 0 errors in case nothing gets converted
    number_of_files = 0
    for media in files_to_convert:
        video_rate, audio_rate, audio_channels = decide_quality(media)
        name, ext = split_ext(media.fileName)
        output_file_path = path.join(dir_path, name + '.mkv')
        if path.isfile(output_file_path):
            print("Output file {} \n\tAlready exists! skipping...".format(output_file_path))
            continue

        accum_input_size += path.getsize(media.filePath)
        number_of_files += 1

        cvt = MediaConverter(media, output_file_path)

        try:
            cvt.createVideoStream(codec, 'crf', video_rate, speed)
        except IndexError:
            print("NO VIDEO FOUND")
        try:
            cvt.createAudioStream(media.audioStreams[0], 'opus', audioBitrate=audio_rate, audioChannels=audio_channels)
        except IndexError:
            print("NO AUDIO FOUND")
        c.append(cvt)

    print("-----  CONVERTING  -----")

    q = MediaConverterQueue(max_processes=concurrency)
    q.add_jobs(c)
    q.run()

    while not q.done:
        time.sleep(5)
        print("Working on {}\n".format(dir_path))

    MB_Min = (accum_input_size/1000000)/(q.total_time/60)
    print("\n\nDone converting {} files in {} at {}".format(number_of_files, dir_path, time.strftime("%I:%M:%S %p")))
    print("Conversion took {}, at an average rate of {} MB/min\n\n".format(seconds_to_timecode(q.total_time), MB_Min))


def decide_quality(qualities, media_object):
    """Chooses the crf quality of the video as well as the bitrate and channels of the audio files from the
    supplied qualities dict.

    :param qualities: dict, see notes at top of file
    :param media_object: MediaObject
    :return:
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

if __name__ == '__main__':
    for folder in dirs_to_convert:
        dir_path = path.join(parent_dir, folder)
        if not path.isdir(dir_path):
            print("Folder {} doesn't seem to exist, aborting!".format(dir_path))
            sys.exit()
        else:
            print("{} Exists!".format(dir_path))
        print()

    for folder in dirs_to_convert:
        d = path.join(parent_dir, folder)
        convert_folder_x265(d)
