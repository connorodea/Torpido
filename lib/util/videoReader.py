import gc
from queue import Queue
from threading import Thread

import cv2

from lib.util.constants import VIDEO_WIDTH
from lib.util.image import resize
from lib.util.logger import Log


class VideoGet:
    """
    Class that continuously gets frames from a VideoCapture object
    with a dedicated thread, which actually speeds up the video
    reading 2 times faster than working in the main UI Thread.

    Attributes
    ----------
    Q : queue
        python queue for storing the frames that are to be processed
    stream : video capture
        open cv stream object that read the video in frames
    stopped : bool
        stream is ended or the video is not ended yet

    Examples
    --------
    Reads the video using the Thread and saving the frames in the queue
    to process them. As the video is read by the Thread the speed increases
    and locking functions of open cv can be skipped.
    """

    def __init__(self, src):
        self.Q = Queue(maxsize=1024)
        self.stream = cv2.VideoCapture(src)
        self.stopped = False

    def start(self):
        """
        Create the thread
        """
        Thread(target=self.get, args=()).start()
        return self

    def get(self):
        """
        Reads the frame from the stream, much faster
        in the thread
        """
        while True:
            if self.stopped:
                return

            if not self.Q.full():
                (grabbed, frame) = self.stream.read()

                if not grabbed:
                    self.stop()
                    return

                frame = resize(frame, width=VIDEO_WIDTH)
                self.Q.put(frame)

    def read(self):
        """
        Get the frame from the queue

        Returns
        -------
        frame : object
            returns the frame to process, if timeout(queue lock) occurs None is returned
        """
        try:
            data = self.Q.get(True, 3)
        except:
            data = None
        return data

    def getCapture(self):
        """
        Returns the video stream of open cv

        Returns
        -------
        object
            stream of the video
        """
        return self.stream

    def more(self):
        """
        checking if the video is still processing or done
        """
        return not self.stopped

    def stop(self):
        """
        Explicitly ending the reading of the video stream. Minor clean ups
        """
        self.stopped = True
        Log.d(f"Garbage collected :: {gc.collect()}")
        self.stream.release()

    def __del__(self):
        del self.Q