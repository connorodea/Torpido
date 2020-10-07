"""
Audio de noising process: this class will read the audio file and using
wavelet transforms a threshold will be added to each window with certain level
"""

import gc
import os

import numpy as np
import pywt
import soundfile
from joblib import dump
from matplotlib import pyplot as plt

from lib.noise.noiseProfiler import NoiseProfiler
from lib.util.cache import Cache
from lib.util.constants import *
from lib.util.logger import Log


def mad(array):
    """
    Median Absolute Deviation: a "Robust" version of standard deviation.
    Indices variability of the sample.
    https://en.wikipedia.org/wiki/Median_absolute_deviation

    Gives variance for the input signal

    Parameters
    ----------
    array : numpy array
        input data from signal
    """
    array = np.ma.array(array).compressed()
    return np.median(np.abs(array - np.median(array)))


def plotSignals(inputData, cleanData):
    """
    Plotting the input signal and the cleaned version.
    Not yet optimized. Heavy on memory

    Spectrogram plotting

    Parameters
    ----------
    inputData : array
        input signal original
    cleanData : array
        cleaned signal
    """
    plt.subplot(211)
    plt.title('Spectrogram for original and cleaned signal')
    plt.specgram(inputData, Fs=44100)
    plt.xlabel('Time')
    plt.ylabel('Frequency')

    plt.subplot(212)
    plt.specgram(cleanData, Fs=44100)
    plt.xlabel('Time')
    plt.ylabel('Frequency')
    plt.show()


class Auditory:
    """
    Audio de noising is done using Wavelet Transform on the input audio signal. The functions read
    the input audio signal in small portions and append the de-noised signal to the output audio
    file that is later merged with the input video file

    Attributes
    ----------
    __fileName : str
        input audio file
    __rate : int
        sample rate of the audio signal in frequency
    __plot : bool
        plot the signal
    __info : object
        sound file object having the info of the audio file
    __energy : list
        list of the ranks for the audio signal
    __audioRankPath : str
        directory to store the rank of the audio
    __silenceThreshold : int
        threshold value to determine the rank
    __cache : Cache
        object of the cache to store the audio file info
    """
    def __init__(self):
        self.__fileName = None
        self.__rate = None
        self.__data = None
        self.__plot = False
        self.__info = None
        self.__energy = None
        self.__audioRankPath = os.path.join(os.getcwd(), RANK_DIR, RANK_OUT_AUDIO)
        self.__silenceThreshold = SILENCE_THRESHOlD
        self.__cache = Cache()

    def startProcessing(self, inputFile, outputFile, plot=False):
        """
        Calculates the de noised signal based on the wavelets
        default wavelet is = db4, mode = per and thresh method = soft.

        The input audio is read in small portions de-noised and appended to the
        audio file in same manner. Also it supports multiple channels and the
        size of the input audio file and output audio files are same so no
        data loss.

        Uses the VISU Shrink thresholding for the noise in the audio signal

        Prints some debug and info Logs

        Parameters
        ----------
        inputFile : str
            input audio file
        outputFile : str
            output audio file
        plot : bool
            True to plot the audio signal

        """
        if os.path.isfile(inputFile) is False:
            Log.e(f"File {inputFile} does not exists")
            return

        self.__fileName = inputFile
        self.__info = soundfile.info(self.__fileName)
        self.__setAudioInfo()
        self.__rate = self.__info.samplerate
        self.__energy = []
        Log.i(f"Audio duration is {self.__info.duration}.")

        with soundfile.SoundFile(outputFile, mode="w", samplerate=self.__rate, channels=self.__info.channels) as out:
            for block in soundfile.blocks(self.__fileName, int(self.__rate * self.__info.duration * AUDIO_BLOCK_PER)):
                # cal all coefficients
                coefficients = pywt.wavedec(block, WAVELET, DEC_REC_MODE)

                # getting the variance of the signal
                sigma = mad(coefficients[- WAVELET_LEVEL])

                # VISU Shrink thresholding by applying the universal threshold proposed by Donoho and Johnstone
                thresh = sigma * np.sqrt(2 * np.log(len(block)))
                coefficients[1:] = (pywt.threshold(i, value=thresh, mode=WAVE_THRESH) for i in coefficients[1:])

                cleaned = pywt.waverec(coefficients, WAVELET, mode=DEC_REC_MODE)
                # recreating the audio signal in original form and writing to the output file
                out.write(cleaned)

                # calculating the audio rank
                self.__energy.extend([self.__getEnergyRMS(block)] * max(1, int(len(block) / self.__rate)))

                if plot:
                    plotSignals(block.T[0], cleaned.T[0])

        dump(self.__energy, self.__audioRankPath)
        Log.i("Audio de noised successfully")
        Log.d(f"Audio ranking length {len(self.__energy)}")
        Log.i("Audio ranking saved .............")
        Log.d(f"Garbage collected :: {gc.collect()}")

    def __getEnergyRMS(self, block):
        """
        RMS = Root Mean Square to calculate the signal data to the dB, if signal
        satisfies some threshold the ranking can be affected and audio portion
        can be ranked
        RMS -> square root of mean of squared data

        Parameters
        ----------
        block : array
            input signal block

        Returns
        -------
        int
            rank for the portion which is then set for all the portion of data
        """
        if np.sqrt(np.mean(block ** 2)) > self.__silenceThreshold:
            return RANK_AUDIO
        return 0

    def __setAudioInfo(self):
        self.__cache.writeDataToCache(CACHE_AUDIO_INFO, self.__info)

    def __getNoiseFromAudio(self):
        """
        Parsed the input audio signal all at once and generates an
        noise profile or the signal and saved to the file

        Writes the noise signal to the file names 'noise.wav'
        """
        data, rate = soundfile.read(self.__fileName)
        filePath = os.path.dirname(self.__fileName)

        noiseSignal = NoiseProfiler(data).getNoiseDataPredicted()
        soundfile.write(os.path.join(filePath, "noise.wav"), noiseSignal, rate)
        Log.i("Noise file generated.")

    def __del__(self):
        """
        clean up
        """
        del self.__cache
        Log.d("Cleaning up.")
