from time import time
from os import mkdir, path


class FileLogger:
    DIRNAME = "ffmpeg_logs"

    def __init__(self):
        if not path.isdir(FileLogger.DIRNAME):
            mkdir(FileLogger.DIRNAME)
        self._filename = str(time()) + "_error.log"
        self._file = None

    def open(self):
        self._file = open(path.join(FileLogger.DIRNAME, self._filename), "w")

    def log(self, log):
        if not self._file.closed:
            self._file.write(str(log) + "\n")
        else:
            self.open()
            self._file.write(str(log) + "\n")

    def close(self):
        self._file.close()

    def __del__(self):
        if not self._file.closed:
            self._file.close()
        del self._file
