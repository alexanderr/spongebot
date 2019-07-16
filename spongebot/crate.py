import os
import random
from pydub import AudioSegment


class Crate:
    def generate(self, *args):
        raise NotImplementedError


class FrameCrate(Crate):
    FRAME_DIRECTORY = 'frames'
    COMMAND = 'ffmpeg -i "%s" -vcodec png -ss %d -s 320x240 -vframes 1 -an -f rawvideo "%s"'
    LENGTH = (11 * 60) - 10

    def __init__(self, user_id, channel):
        self.frame = ''
        self.channel = channel
        self.crate_id = 0
        self.user_id = user_id
        self.episode = None

    def generate(self, crate_manager):
        self.episode = random.choice(crate_manager.bot.episode_data)

        # too lazy to have ffmpeg read the whole file for the length.
        # Use the episode name instead of episode number because of inconsistencies.
        if self.episode.name == 'reef blower':
            # Special case: this episode is 3 mins long.
            t = random.randint(5, (60 * 3) - 10)
        elif self.episode.name == 'gary takes a bath':
            # 6 mins
            t = random.randint(5, (60 * 6) - 10)
        elif self.episode.name == 'christmas who':
            # 20 mins
            t = random.randint(5, (60 * 20) - 10)
        else:
            # 11 mins usually
            t = random.randint(5, self.LENGTH)

        inpath = self.episode.path

        directory = os.path.join('frames', self.user_id)

        if not os.path.isdir(directory):
            os.mkdir(directory)

        outpath = os.path.join(directory, str(self.crate_id)) + '.png'

        os.system(self.COMMAND % (inpath, t, outpath))

        self.frame = outpath
        crate_manager.generated_crate_queue.append(self)


class VoicelineCrate(Crate):
    VOICELINE_DIRECTORY = 'voicelines'

    def __init__(self, user_id, channel):
        self.voiceline = ''
        self.channel = channel
        self.crate_id = 0
        self.user_id = user_id
        self.episode = ''
        self.type = 0

    def generate(self, crate_manager):
        self.episode = random.choice(crate_manager.bot.episode_data)

        inpath = self.episode.path

        audio = AudioSegment.from_file(inpath, 'avi')

        intro = 5
        outro = 5

        rng = random.random()
        if rng < .10:
            clip = 7
            self.type = 3
        elif rng < .33:
            clip = 5
            self.type = 2
        else:
            clip = 3
            self.type = 1

        length = int(len(audio) / 1000) - outro - clip

        start = random.randint(intro, length) * 1000  # time in ms

        voiceline = audio[start:start + (clip * 1000)]

        s = AudioSegment.silent(duration=250)
        voiceline = voiceline.append(s, crossfade=250)

        directory = os.path.join(self.VOICELINE_DIRECTORY, str(self.user_id))

        if not os.path.isdir(directory):
            os.mkdir(directory)

        outpath = os.path.join(directory, '%s.wav' % self.crate_id)

        voiceline.export(outpath, format='wav')

        self.voiceline = outpath

        crate_manager.generated_crate_queue.append(self)
