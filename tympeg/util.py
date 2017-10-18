from os import path, listdir


def split_ext(file_name):
    index = file_name.rfind('.')
    name = file_name[:index]
    ext = file_name[index:]
    return name, ext


def list_dirs(dir_path):
    dirs = []
    for item in listdir(dir_path):
        if path.isdir(path.join(dir_path, item)):
            dirs.append(path.join(dir_path, item))
    return dirs


def list_files(dir_path):
    files = []
    for item in listdir(dir_path):
        if path.isfile(path.join(dir_path, item)):
            files.append(path.join(dir_path, item))
    return files


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

def get_dir_size_recursive(directoryPath):
    """
    Returns the size of a directory's contents (recursive) in bytes.
    :param directoryPath: string, path of directory to be analyzed
    :return: int, size of sum of files in directory in bytes
    """
    # Collect directory size recursively
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directoryPath):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


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