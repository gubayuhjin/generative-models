#!/usr/bin/python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

"""
Authors:    Dario Cazzani
"""

import numpy as np
import random
import sys
sys.path.append('../')
from helpers.signal_processing import wav_to_floats
from config import set_config
import glob


def CMajorScaleDistribution(batch_size):
    sample_rate = 16000
    seconds = 1
    t = np.linspace(0, seconds, sample_rate*seconds)  # 16000 Hz sampling rate
    C_major_scale = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]
    intensities = np.linspace(0.2, 1., 9)
    num_notes = 4
    note_length = int(sample_rate * seconds / num_notes)
    while True:
        try:
            batch = []
            for i in range(batch_size):
                # select random note
                sounds = []
                for note in range(num_notes):
                    pitch = C_major_scale[np.random.randint(len(C_major_scale))]
                    intensity = intensities[np.random.randint(len(intensities))]
                    sound = np.sin(2*np.pi*t[:note_length]*pitch)
                    noise = [random.gauss(0.0, 1.0) for i in range(len(sound))]
                    noise_level = np.random.rand()*0.09 + 0.01
                    noisy_sound = sound + noise_level * np.asarray(noise)
                    noisy_sound *= intensity
                    sounds.append(noisy_sound)
                sounds = np.concatenate(sounds).ravel()

                batch.append(sounds)

            yield np.asarray(batch)

        except Exception as e:
            print('Could not produce batch of sinusoids because: {}'.format(e))
            sys.exit()

def SinusoidDistribution(batch_size):
    sample_rate = 16000
    seconds = 1
    t = np.linspace(0, seconds, sample_rate*seconds)  # 16000 Hz sampling rate
    num_notes = 1
    note_length = int(sample_rate * seconds / num_notes)
    while True:
        try:
            batch = []
            for i in range(batch_size):
                # select random note
                sounds = []
                for note in range(num_notes):
                    pitch = np.floor(np.random.rand()*1000) + 500.
                    sound = np.sin(2*np.pi*t[:note_length]*pitch)
                    sounds.append(sound)
                sounds = np.concatenate(sounds).ravel()
                noise = [random.gauss(0.0, 1.0) for i in range(sample_rate*seconds)]
                noisy_sound = sounds + 0.08 * np.asarray(noise)
                batch.append(noisy_sound)

            yield np.asarray(batch)

        except Exception as e:
            print('Could not produce batch of sinusoids because: {}'.format(e))
            sys.exit()


class NSynthGenerator(object):
    def __init__(self, audiofiles, batch_size):
        self.audiofiles = audiofiles
        self.batch_size = batch_size
        self.__generate_random_access_idx()
        self.audio_length = 16000 #samples
        self.batch = np.zeros((self.batch_size, self.audio_length))

    def __iter__(self):
        return self

    def __generate_random_access_idx(self):
        self.random_access_idx = np.random.permutation(len(self.audiofiles))[:self.batch_size]

    def __load(self):
        for idx, el in enumerate(list(self.random_access_idx)):
            # load random audio file
            filename = self.audiofiles[el]
            audio, rate = wav_to_floats(filename)
            assert(len(audio) >= self.audio_length)
            self.batch[idx, :] = audio[:self.audio_length]

    def __next__(self):
        while True:
            self.__generate_random_access_idx()
            self.__load()
            return self.batch

def main():
    data = CMajorScaleDistribution(32)
    parser = set_config()
    (options, args) = parser.parse_args()
    audiofiles = glob.glob(options.DATA_PATH + '/nsynth-test/audio/*wav')
    nsynth = NSynthGenerator(audiofiles, 32)
    batch = data.__next__()
    batch = nsynth.__next__()
    print(batch.shape)

if __name__ == '__main__':
    main()
