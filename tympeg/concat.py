import subprocess
from os import path, getcwd, remove, rename, rmdir

from .mediaobject import MediaObject, makeMediaObjectsInDirectory

from .util import list_files


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
    listFileName = path.join(str(getcwd()), "tempFfConcat.txt")
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
        print("Error: CalledProcess in ttympeg.ffConcat()")
        print("CalledProcessError: " + str(cpe))
        processData = None
    finally:
        remove(listFileName)

    return processData


def concat_files_in_directory(input_dir_path, alphabetical=True, delete_source=False, output_dir_path=""):
    """
    Attempts to concat ALL files in a directory, be careful! Places file in parent folder with first file's name
    then deletes source files if specified.
    :param input_dir_path: string, path to directory of files to be concatenated
    :param alphabetical: boolean, whether or not to alphabetize the files during concatenation
    :param delete_source: boolean, deletes source files when completed
    :param output_dir_path: string, optionally specify output directory
    :return: string, path of output file
    """

    media_object_array = makeMediaObjectsInDirectory(input_dir_path)
    if alphabetical:
        media_object_array = sorted(media_object_array, key=lambda media: media.fileName)

    # Decide output path, either parameter or default
    if output_dir_path != "":
        output_dir = output_dir_path
    else:
        output_dir, tail = path.split(input_dir_path)

    # Output filename is just the first file in the array of source files
    output_path = path.join(output_dir, media_object_array[0].fileName)

    files = list_files(input_dir_path)
    num_files = len(files)

    if num_files == 1:  # if the directory only has one file, just move it
        rename(files[0], path.join(output_path))
    elif num_files == 0:  # nothing in the dir, just return
        return
    else:
        ffConcat(media_object_array, output_path)
        if delete_source and path.isfile(output_path):  # Double check output file exists!
            for file in files:
                remove(file)
            rmdir(input_dir_path)

    return output_path
