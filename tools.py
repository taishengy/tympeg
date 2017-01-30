from pympeg import *
import time


def list_dirs(dir_path):
    dirs = []
    for item in os.listdir(dir_path):
        if os.path.isdir(os.path.join(dir_path, item)):
            dirs.append(os.path.join(dir_path, item))
    return dirs


def concat_files_in_directory(input_dir_path, alphabetical=True):
    """
    Attempts to concat ALL files in a directory, be careful!
    :param input_dir_path: string, path to directory of files to be concatenated
    :param alphabetical: boolean, whether or not to alphabetize the files during concatenation
    :return: void
    """

    media_object_array = makeMediaObjectsInDirectory(input_dir_path)
    if alphabetical:
        media_object_array = sorted(media_object_array, key=lambda media: media.fileName)
    output_path, tail = path.split(input_dir_path)
    ffConcat(media_object_array, path.join(output_path, media_object_array[0].fileName))


def quick_clip(file_path, start_time, end_time, output_path=''):
    """
    Clips file between start_time and end_time. Copies all stream in file between time codes.
    :param file_path: string, path of file to clip
    :param start_time: string, timecode of when to start clip
    :param end_time: string, timecode of when to stop clip
    :param output_path: string, optional, path of output file
    :return:
    """
    media = MediaObject(file_path)
    cvt = MediaConverter(media, output_path)

    for videoIndex in media.videoStreams:
        cvt.createVideoStream('copy', 'copy', 0, videoStream=videoIndex)

    for audioIndex in media.audioStreams:
        cvt.createAudioStream(audioEncoder='copy', audioStream=audioIndex)

    cvt.createSubtitleStreams(media.subtitleStreams)
    cvt.clip(start_time, end_time)


def convert_files_in_dir_to_vcodec(input_folder, video_codec, video_encoder, rate_control_method, video_rate, speed,
                                   audio_encoder, audio_bitrate, channels):
    """ Searches directory for videos NOT encoded with video_codec, moves them to a separate file and encodes them
     to the selected codec, saving the encodes in the original directory. Retains all streams.

    :param input_folder: string, the folder to be searched and converted
    :param video_codec: string, video Codec to search for 'hevc' for h265 video
    :param video_encoder: string, video encoder ffmpeg should use ('x265', 'x264', 'vp8', 'vp9')
    :param rate_control_method: string, rate control method ('crf', 'cbr', 'vbr)
    :param video_rate: int, rate of video. Either quality factor or bitrate
    :param speed: string, speed of x26X family encoders
    :param audio_encoder: string, audio encoder ('opus', 'aac', 'fdk', etc...)
    :param audio_bitrate: int, bitrate of audio
    :param channels: string, channel layout of audio ('mono', 'stereo')
    :return:
    """

    # create original folder if it doesn't exist
    original_files_dir = path.join(input_folder, "original_files/")

    # figure out what isn't the codec and move those to original_files_dir
    sorting_media_array = makeMediaObjectsInDirectory(input_folder)
    if len(sorting_media_array) < 1:
        return

    nothing_to_convert = True
    for media in sorting_media_array:
        if media.videoCodec != str(video_codec):
            nothing_to_convert = False
            if not path.isdir(original_files_dir):
                os.mkdir(original_files_dir)
            os.rename(path.join(input_folder, str(media.fileName)), path.join(original_files_dir, str(media.fileName)))

    # convert files in original_files folder
    if nothing_to_convert:
        return
    converting_media_array = makeMediaObjectsInDirectory(original_files_dir)
    total_files = str(len(converting_media_array))
    print("\n\nConverting " + total_files + " files...\n\n")

    count = 0
    input_file_size = 0
    output_file_size = 0
    time_start = time.time()
    total_input_size = get_dir_size(original_files_dir)/1000000

    for media in converting_media_array:
        name, ext = path.splitext(media.fileName)
        output_file_path = path.join(input_folder, name + '.mkv')
        cvt = MediaConverter(media, output_file_path)

        cvt.createVideoStream(video_encoder, rate_control_method, video_rate, speed)

        for audioStream in range(0, len(media.audioStreams)):
            cvt.createAudioStream(media.audioStreams[audioStream], audio_encoder, audio_bitrate, audioChannels=channels)

        cvt.createSubtitleStreams(media.subtitleStreams)
        count += 1
        print("Converting file " + str(count) + ' of ' + total_files + ":")
        print("\t{0} ({1:,.2f} MB)\n".format(media.filePath, path.getsize(original_files_dir + media.fileName)/1000000))

        start = time.time()
        cvt.convert()
        end = time.time()

        output_file_size += path.getsize(output_file_path)/1000000
        input_file_size += path.getsize(original_files_dir + media.fileName)/1000000
        minutes = (end - start)/60
        input_rate = (path.getsize(original_files_dir + media.fileName)/1000000)/minutes
        avg_rate = input_file_size/((end - time_start)/60)
        eta_hours, eta_mins = divmod(round((total_input_size - input_file_size)/avg_rate, 0), 60)

        print('\nCompleted file {0} of {1} in {2:,.2f} min'.format(count, total_files, minutes))
        print('Completed file at input rate of: {0:,.2f} MB/min'.format(input_rate))
        print('Average rate of: {0:,.2f} MB/min'.format(avg_rate))
        print('ETA: {0}:{1}'.format(int(eta_hours), int(eta_mins)))
        print('Total input converted: {0:,.2f} MB of {1:,.2f} MB'.format(input_file_size, total_input_size))
        print('Total output size: {0:,.2f} MB'.format(output_file_size))
        print('Output/Input ratio: {0:,.3f}'.format(output_file_size/input_file_size))
        print("\n\n")

    time_end = time.time()
    total_seconds = time_end - time_start
    m, s = divmod(total_seconds, 60)
    if m == 0:
        minutes = 1
    else:
        minutes = m
    h, m = divmod(m, 60)
    print("Total operation completed in: %d:%02d:%02d" % (h, m, s))
    print("Total size of files converted: " + str(input_file_size) + " MB => " + str(output_file_size) + " MB")
    print("Average rate of input converted: " + str((input_file_size/minutes)) + " MB/min")


def convert_folder_x265_profile(input_folder, profile):
    video_encoder = 'x265'
    rate_control_method = 'crf'
    audio_encoder = 'opus'

    if profile == 'low':
        rate = 25
        speed = 'veryfast'

        audio_bitrate = 48
        channels = 'mono'

    elif profile == 'medium':
        rate = 23
        speed = 'veryfast'

        audio_bitrate = 96
        channels = 'stereo'

    elif profile == 'high':
        rate = 20
        speed = 'veryfast'

        audio_bitrate = 128
        channels = 'stereo'

    else:
        print("Profile specified not valid. Specify 'high', 'medium' or 'low'.")
        return

    convert_files_in_dir_to_vcodec(input_folder, 'hevc', video_encoder, rate_control_method, rate, speed, audio_encoder,
                                   audio_bitrate, channels)


def concat_files_grouped_in_folders(parent_dir):
    dirs = list_dirs(parent_dir)
    for directory in dirs:
        print(directory)
        concat_files_in_directory(directory)

def decide_x265_quality(media_object):
    duration = media_object.duration
    file_size = media_object.file_size
    width = media_object.width
    height = media_object.height
    pixels = media_object.width * media_object.height
    video_bitrate = media_object.video_bitrate
    audio_bitrate = media_object.audio_bitrate
    framerate = media_object.framerate_dec

    bits_pixel = video_bitrate / (pixels * framerate)

    print("Duration: {}".format(duration))
    print("FileSize: {}".format(file_size))
    print("Width: {}".format(width))
    print("Height: {}".format(height))
    print("Pixels: {}".format(pixels))
    print("Video Bitrate: {}".format(video_bitrate))
    print("Audio Bitrate: {}".format(audio_bitrate))
    print("Video Framerate: {}".format(framerate))
    print("Bits per Pixel: {}".format(bits_pixel))


