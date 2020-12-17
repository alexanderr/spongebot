import asyncio
import datetime
import json
import logging
import os
from asyncio import coroutine

from discord.client import Client

from spongebot.commandmanager import CommandManager
from spongebot.cratemanager import CrateManager
from spongebot.requestmanager import RequestManager
from spongebot.userdb import UserMongoDB


class Spongebot(Client):
    def __init__(self):
        Client.__init__(self)

        self.config = {}

        self.logger = None

        self.episode_data = []
        self.episode_pool = []
        self.current_episode = None
        self.episode_player = None
        self.voiceline_player = None
        self.point_task = None

        self.setup_logging()

        self.command_manager = CommandManager(self)
        self.userdb = UserMongoDB(self)
        self.crate_manager = CrateManager(self)
        self.request_manager = RequestManager(self)

    @coroutine
    def authenticate(self):
        yield from self.login(self.config['token'])
        yield from self.connect()

    def setup_logging(self):
        self.logger = logging.getLogger('spongebot')
        self.logger.setLevel(logging.DEBUG)

        now = datetime.datetime.now()

        filename = 'spongebot-%s-%s-%s.log' % (now.day, now.month, now.year)

        path = os.path.join('logs', filename)

        handler = logging.FileHandler(filename=path,
                                      encoding='utf-8',
                                      mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
        self.logger.addHandler(handler)

    def load_config(self):
        with open('config.json', 'r') as f:
            try:
                self.config = json.load(f)
            except json.JSONDecodeError as e:
                self.log('Error parsing configuration!')
                raise e

    def parse_episode_data(self):
        content_directory = self.config.get('content_directory', 'content')
        content_extension = self.config.get('content_extension', 'avi')

        for root, dirs, files in os.walk(content_directory):
            for f in files:
                path = os.path.join(root, f)
                if not os.path.isfile(path):
                    continue

                filename, extension = f.rsplit('.', 1)
                filename = filename.lower()

                if extension != content_extension:
                    continue

                episode_number, episode_name = filename.split(' ', 1)
                season, episode = int(episode_number[0]), int(episode_number[1:])
                self.episode_data.append(Episode(filename, season, episode, episode_name, path))
                self.log('Found episode %s' % self.episode_data[-1])

        self.episode_pool = list(range(len(self.episode_data)))

    async def on_ready(self):
        self.crate_manager.initialize_tasks()
        self.log('Client is ready!')

    async def on_message(self, message):
        if message.content.startswith(self.config.get('command_delimeter', '$')):
            # This is a command.
            message.content = message.content[1:]
            await self.on_command(message)

    async def on_command(self, message):
        args = message.content.split(' ')
        command = args.pop(0)

        data = self.userdb.get(message.author)
        access = 0
        if data:
            access = data.access_level
        else:
            self.userdb.insert(message.author)
            data = self.userdb.get(message.author)

        self.log('%s used command %s with arguments %s.' % (message.author.name, command, str(args)))

        if not hasattr(self.command_manager, 'c_' + command):
            await self.send_message(message.channel, 'Unknown command ```%s```' % command)
            return

        func = getattr(self.command_manager, 'c_' + command)
        if args:
            await func(message, command, access, *args)
        else:
            await func(message, command, access)

    async def play_episode(self, text_channel, voice):
        play_message = ''
        play_message += '```Playing episode %s from season %s.```\n' % \
                        (self.current_episode.episode, self.current_episode.season)
        play_message += '```Every minute you listen to the episode you will gain 1 point.```\n'
        play_message += "```Use $info to see your stats.```\n"
        await self.send_message(text_channel,  play_message)

        self.log('Playing episode %s...' % str(self.current_episode))

        def after():
            coro = self.on_episode_end(text_channel.server)
            future = asyncio.ensure_future(coro, loop=self.loop)
            future.result()

        if self.voiceline_player is not None and not self.voiceline_player.is_done():
            self.voiceline_player.stop()

        if self.episode_player is None or self.episode_player.is_done():
            self.episode_player = voice.create_ffmpeg_player(self.current_episode.path, after=after)
            self.episode_player.start()
        else:
            self.episode_player.stop()
            self.episode_player = voice.create_ffmpeg_player(self.current_episode.path, after=after)
            self.episode_player.start()

        if self.point_task:
            self.point_task.cancel()
            self.point_task = None

        self.point_task = self.loop.call_later(60, self.give_points, text_channel.server)

    async def on_episode_end(self, server):
        voice = self.voice_client_in(server)

        if not voice:
            return

        for member in voice.channel.voice_members:
            if member.voice.deaf or member.voice.self_deaf or member.voice.is_afk:
                continue

            self.userdb.update(member, {'$inc': {'episodes_watched': 1}})
            self.userdb.update(member, {'$push': {'episode_list': str(self.current_episode)}})

        self.current_episode = None

    def give_points(self, server):
        if self.episode_player is None:
            return

        if self.episode_player.is_done():
            return

        voice = self.voice_client_in(server)

        if not voice:
            return

        self.log('Updating points...')

        for member in voice.channel.voice_members:
            if member.voice.deaf or member.voice.self_deaf or member.voice.is_afk:
                continue

            if not self.userdb.exists(member):
                self.userdb.insert(member)

            self.userdb.update(member, {'$inc': {'current_points': 1, 'total_points': 1}})

        self.point_task = self.loop.call_later(60, self.give_points, server)

    def log(self, msg, level=logging.DEBUG):
        self.logger.log(level=level, msg=msg)


class Episode:
    def __init__(self, filename, season, episode, name, path):
        self.filename = filename
        self.season = season
        self.episode = episode
        self.name = name
        self.path = path

    def __str__(self):
        return self.name
