import subprocess
from os import path, mkdir

from tympeg.util import renameFile


class StreamSaver:
    """
    Class that is responsible for writing network streams to disk. StreamSaver.run() must be called after initialization
    """
    def __init__(self, input_stream, output_file_path_ts, verbosity=24):
        """

        :param input_stream: String, generally a url to a .m3u8 playlist
        :param output_file_path_ts: String, output file. Any extension specified here will be rewritten to .ts. Avoid '.' in file names.
        :param verbosity: int, FFMPEG verbosity level. Defaults fairly high to keep warning spam out of stdout.
        """
        self.file_writer = None
        self.analyzeduration = 5000000  # ffmpeg default value (milliseconds must be integer)
        self.probesize = 5000000  # ffmpeg default value (bytes must be > 32 and integer)
        directory, file_name = path.split(output_file_path_ts)

        # make sure output is .ts file for stable writing
        file_name, ext = file_name.split('.')
        file_name += '.ts'

        if not path.isdir(directory):
            mkdir(directory)
        if path.isfile(output_file_path_ts):
            file_name = renameFile(file_name)
            output_file_path_ts = path.join(directory, file_name)

        self.args = ['ffmpeg', '-v', str(verbosity), '-analyzeduration', str(self.analyzeduration),
                     '-probesize', str(self.probesize), '-i', str(input_stream), '-c', 'copy', output_file_path_ts]

    def run(self):
        """
        Calls ffmpeg with StreamSaver arguments. Begins writing stream to disk.
        :return:
        """
        self.file_writer = subprocess.Popen(self.args)

    def quit(self):
        """
        Terminates StreamSaver.
        :return:
        """

        self.file_writer.terminate()
