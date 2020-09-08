import os
import time

import cv2
import numpy as np
from joblib import dump

from lib.util.constants import *
from lib.util.videoReader import VideoGet

"""
This file is for calculating the textual ranking for the video
, the textual ranking is done by detecting text in the video.
Text detection is achieved by using EAST Text Detection model 
of OpenCV, this model can detect text and return confidences and
geometry for the sections that contain the text.
If mixed with text extraction it can give text from the image.
"""


class Textual:
    def __init__(self):
        """
        initializing the constants and model
        loading the model in the memory
        """
        self.fps = None
        self.frameCount = None
        self.textRanks = None
        self.minConfidence = TEXT_MIN_CONFIDENCE
        self.WIDTH = 320
        self.HEIGHT = 320
        self.skipFrames = TEXT_SKIP_FRAMES
        self.textRankPath = os.path.join(RANK_DIR, RANK_OUT_TEXT)

        # initializing the model
        # reading the model in the memory
        self.net = cv2.dnn.readNet(TEXT_EAST_MODEL_PATH)

        # adding output layers to the model
        self.layerNames = ["feature_fusion/Conv_7/Sigmoid",
                           "feature_fusion/concat_3"]

    def startProcessing(self, inputFile, display=False):
        """
        processing the input video file, performing text detection only on the
        frames that satisfies the skipped, then getting the confidence of all
        sections and taking the mean and then saving the ranks for the video.
        :param inputFile: string, input video file
        :param display: bool, true to display the video while processing
        :return: None
        """

        if os.path.isfile(inputFile) is False:
            print(f"[ERROR] File {inputFile} does not exists")
            return

        videoGetter = VideoGet(inputFile).start()
        myClip = videoGetter.stream

        self.fps = myClip.get(cv2.CAP_PROP_FPS)
        self.frameCount = myClip.get(cv2.CAP_PROP_FRAME_COUNT)
        self.skipFrames = self.fps * self.skipFrames

        # maintaining the ranks for text detection
        count = 0
        self.textRanks = []

        while True:
            if videoGetter.stopped:
                videoGetter.stop()
                break

            frame = videoGetter.frame

            if frame is None:
                break

            # resizing the frame to a multiple of 32 x 32
            count += 1
            (W, H) = 320, 320

            # resizing the frame
            frame = cv2.resize(frame, (W, H))

            if count % self.skipFrames == 0:
                #  making the image blob
                blob = cv2.dnn.blobFromImage(frame, 1.0, (W, H), (123.68, 116.78, 103.94),
                                             swapRB=True, crop=False)
                start = time.time()
                self.net.setInput(blob)
                (scores, geometry) = self.net.forward(self.layerNames)
                end = time.time()

                print(f"[INFO] Text detection took :: {end - start} s")

                (numRows, numCols) = scores.shape[2:4]
                confidences = []

                # try to optimize this part
                for y in range(0, numRows):
                    scoresData = scores[0, 0, y]
                    for x in range(0, numCols):
                        if scoresData[x] < self.minConfidence:
                            continue
                        confidences.append(scoresData[x])

                # check if the confidence satisfies the threshold
                # print(f"Average confidence :: {np.mean(confidences)}")
                if len(confidences) > 1 and np.mean(confidences) > 0.5:
                    self.textRanks.extend([RANK_TEXT] * int(self.skipFrames))
                else:
                    self.textRanks.extend([0] * int(self.skipFrames))

            if display:
                cv2.imshow("Text Detection", frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

        # clearing the memory
        myClip.release()
        videoGetter.stop()
        cv2.destroyAllWindows()

        # calling the normalization of ranking
        self.timedRankingNormalize()

    def timedRankingNormalize(self):
        """
        since ranking is added to frames, since frames are duration * fps
        and audio frame system is different since frame are duration * rate
        so we need to generalize the ranking system
        sol: ranking sec of the video and audio, for than taking mean of the
        frames to generate rank for video.
        since ranking is 0 or 1, the mean will be different and we get more versatile
        results.

        we will read the list and slice the video to get 1 sec of frames and get
        mean/average as the rank for the 1 sec
        :return: None
        """
        textNormalize = []
        for i in range(0, int(self.frameCount), int(self.fps)):
            if i + int(self.fps) < self.frameCount:
                textNormalize.append(np.mean(self.textRanks[i: i + int(self.fps)]))

        # saving all processed stuffs
        dump(textNormalize, self.textRankPath)
        print(f"[INFO] Textual rank length {len(textNormalize)}")
        print("[INFO] Textual ranking saved .............")
