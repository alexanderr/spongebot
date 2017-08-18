import random
import datetime
import os

from spongebot.constants import RANKS
from spongebot.botrequest import SellRequest, BotRequestException


# Context
PUBLIC = 0
PRIVATE = 1
BOTH = 2


# Access levels (WIP)
USER = 0
VIP = 100
ADMIN = 200


# longest decorator ever!!!!
def command(context, access, types=tuple()):
    def real_decorator(func):
        def wrapper(*args, **kwargs):
            command_manager = args[0]
            source = args[1]
            command_name = args[2]
            current_access = args[3]

            if context == PRIVATE:
                if not source.channel.is_private:
                    return command_manager.invalid_context(source, command_name, context)
            elif context == PUBLIC:
                if source.channel.is_private:
                    return command_manager.invalid_context(source, command_name, context)

            if access > current_access:
                return command_manager.invalid_access(source, command_name, access)

            nargs = [command_manager, source]

            for i in range(len(types)):
                t = types[i]
                arg = args[i + 4]

                if t == int:
                    try:
                        arg = int(arg)
                    except ValueError:
                        return command_manager.invalid_arguments(source, command_name)
                    else:
                        nargs.append(arg)
                elif t == float:
                    try:
                        arg = float(arg)
                    except ValueError:
                        return command_manager.invalid_arguments(source, command_name)
                    else:
                        nargs.append(arg)
                else:
                    nargs.append(arg)

            return func(*nargs, **kwargs)

        return wrapper
    return real_decorator


class CommandManager:
    def __init__(self, bot):
        self.bot = bot

    @command(context=PUBLIC, access=USER)
    async def c_join(self, source):
        channel = source.author.voice_channel

        if not channel:
            await self.bot.send_message(source.channel, '```You are not in a voice channel!```')
            return

        voice = self.bot.voice_client_in(channel.server)

        if not voice:
            voice = await self.bot.join_voice_channel(channel)
        elif voice.channel != channel:
            voice = await voice.move_to(channel)
        else:
            await self.bot.send_message(source.channel, '```I am already in the channel!```')

        def after():
            import datetime
            now = datetime.datetime.now()
            if now.hour < 6:
                player = voice.create_ffmpeg_player('night.wav')
                player.start()

        player = voice.create_ffmpeg_player('ready.wav', after=after)
        player.start()

    @command(context=PUBLIC, access=ADMIN, types=(str,))
    async def c_joinchannel(self, source, channelId):
        channel = self.bot.get_channel(channelId)

        if not channel:
            await self.bot.send_message(source.channel, '```Invalid channel!```')
            return

        voice = self.bot.voice_client_in(channel.server)

        if not voice:
            await self.bot.join_voice_channel(channel)
        elif voice.channel != channel:
            await voice.move_to(channel)
        else:
            await self.bot.send_message(source.channel, '```I am already in the channel!```')

    @command(context=PUBLIC, access=USER)
    async def c_play(self, source):
        if self.bot.episode_player and not self.bot.episode_player.is_done():
            await self.bot.send_message(source.channel, 'Sorry, an episode is already playing!')
            return

        if self.bot.point_task:
            self.bot.point_task.cancel()
            self.bot.point_task = None

        voice = self.bot.voice_client_in(source.channel.server)
        voice_channel = source.author.voice_channel

        if not voice_channel:
            await self.bot.send_message(source.channel, '```You are not in a voice channel!```')
            return

        if not voice:
            voice = await self.bot.join_voice_channel(voice_channel)
        elif voice.channel != voice_channel:
            voice.move_to(voice_channel)
            voice = self.bot.voice_client_in(source.channel.server)

        if len(self.bot.episode_pool) == 0:
            self.bot.episode_pool = list(range(len(self.bot.episode_data)))

        index = random.randint(0, len(self.bot.episode_pool))

        self.bot.current_episode = self.bot.episode_data[self.bot.episode_pool.pop(index)]

        await self.bot.play_episode(source.channel, voice)

    @command(context=PUBLIC, access=ADMIN)
    async def c_leave(self, source):
        if self.bot.episode_player:
            self.bot.episode_player.stop()
            self.bot.episode_player = None
        if self.bot.voiceline_player:
            self.bot.voiceline_player.stop()
            self.bot.voiceline_player = None

        if self.bot.point_task:
            self.bot.point_task.cancel()
            self.bot.point_task = None

        voice = self.bot.voice_client_in(source.channel.server)
        if not voice:
            return

        await voice.disconnect()

    @command(context=PUBLIC, access=USER, types=(str,))
    async def c_request(self, source, episode):
        if self.bot.episode_player and not self.bot.episode_player.is_done():
            await self.bot.player.send_message(source.channel, 'Sorry, an episode is already playing!')
            return

        if self.bot.point_task:
            self.bot.point_task.cancel()
            self.bot.point_task = None

        voice = self.bot.voice_client_in(source.channel.server)

        if source.author.voice_channel:
            if not voice:
                voice = await self.bot.join_voice_channel(source.author.voice_channel)
            elif voice.channel != source.author.voice_channel:
                voice = await voice.move_to(source.author.voice_channel)

        episode_data = None

        for e in self.bot.episode_data:
            if e.filename == episode:
                episode_data = e

        if episode_data is None:
            await self.bot.send_message(source.channel, 'Sorry, that episode does not exist!')
            return

        self.bot.current_episode = episode_data

        await self.bot.play_episode(source.channel, voice)

    @command(context=PUBLIC, access=ADMIN)
    async def c_skip(self, source):
        if self.bot.point_task:
            self.bot.point_task.cancel()
            self.bot.point_task = None

        if self.bot.episode_player:
            self.bot.episode_player.stop()

    @command(context=BOTH, access=USER)
    async def c_info(self, source):
        data = self.bot.userdb.get(source.author)

        if data is None:
            self.bot.userdb.insert(source.author)
            data = self.bot.userdb.get(source.author)

        cdate = datetime.datetime.fromtimestamp(int(data.create_date)).strftime('%Y-%m-%d %H:%M:%S')

        rank = ''

        for key in sorted(RANKS.keys()):
            if key <= data.total_points:
                rank = RANKS[key]

        nmessage = ''
        nmessage += '%s\n' % source.author.mention
        nmessage += '```'
        nmessage += 'First started: %s CST\n' % cdate
        nmessage += 'Current Points: %d\n' % data.current_points
        nmessage += 'Total Points: %d\n' % data.total_points
        nmessage += 'Crates Opened: %d\n' % data.crates_opened
        nmessage += 'Rank: %s\n' % rank
        nmessage += 'Episodes watched: %d' % data.episodes_watched
        nmessage += '```'

        await self.bot.send_message(source.channel, nmessage)

    @command(context=PUBLIC, access=USER, types=(int,))
    async def c_voiceline(self, source, name):
        vldir = os.path.join('voicelines', source.author.id)
        if not os.path.isdir(vldir):
            await self.bot.send_message(source.channel,
                                           "```You don't have any voicelines unlocked. Try opening some crates.```")
            return

        if self.bot.current_episode is not None:
            await self.bot.send_message(source.channel, "```An episode is playing! Wait until it is over.```")
            return

        if self.bot.episode_player and not self.bot.episode_player.is_done():
            await self.bot.send_message(source.channel, "```An episode is playing! Wait until it is over.```")
            return

        # Get the user data
        user = self.bot.userdb.get(source.author.id)
        if user is None or len(user.inventory) == 0:
            await self.bot.send_message(source.channel, '```You do not own any voicelines.```')

        # Get the voice line from the name
        try:
            voiceline = [item for item in user.inventory if item.name == name and item.type == 'voiceline'][0]
        except IndexError:
            await self.bot.send_message(source.channel, '```Invalid voiceline specified.```')
            return

        # Check if we have this voiceline in our file system
        try:
            fpath = os.path.join(vldir, str(voiceline.idx) + '.wav')
            if not os.path.isfile(fpath):
                raise IOError
        except IOError:
            await self.bot.send_message(source.channel, '```Failed to find voiceline.```')
        else:
            channel = source.author.voice.voice_channel
            if not channel:
                await self.bot.send_message(source.channel, "```You are not in a voice channel.```")
                return

            voice = self.bot.voice_client_in(channel.server)
            if not voice:
                voice = await self.bot.join_voice_channel(channel)
            elif voice.channel != source.author.voice_channel:
                voice = await voice.move_to(channel)

            if self.bot.voiceline_player and not self.bot.voiceline_player.is_done():
                self.bot.voiceline_player.stop()

            self.bot.voiceline_player = voice.create_ffmpeg_player(fpath)
            self.bot.voiceline_player.start()

    @command(context=PRIVATE, access=USER)
    async def c_opencrate(self, source):
        await self.bot.crate_manager.generate_crate(source)

    @command(context=PRIVATE, access=USER, types=(int,))
    async def c_gallery(self, source, name):
        framedir = os.path.join('frames', source.author.id)
        if not os.path.isdir(framedir):
            await self.bot.send_message(source.channel, '```You have no frames yet! Try opening some crates!```')
            return

        # Get the user data
        user = self.bot.userdb.get(source.author.id)
        if user is None or len(user.inventory) == 0:
            await self.bot.send_message(source.channel, '```You do not own any frames.```')

        # Get the voice line from the name
        try:
            frame = [item for item in user.inventory if item.name == name and item.type == 'frame'][0]
        except IndexError:
            await self.bot.send_message(source.channel, '```Invalid frame specified.```')
            return

        # Check if the frame is in our file system
        try:
            fpath = os.path.join(framedir, str(frame.idx) + '.png')
            f = open(fpath, 'rb')
        except IOError:
            await self.bot.send_message(source.channel, '```Invalid index specified.```')
        else:
            createTime = os.stat(fpath).st_ctime
            cdate = datetime.datetime.fromtimestamp(int(createTime)).strftime('%Y-%m-%d %H:%M:%S')

            await self.bot.send_message(source.channel, '```Opened %s CST:```' % cdate)
            await self.bot.send_file(source.channel, f)

            f.close()

    @command(context=PRIVATE, access=USER, types=(str, str))
    async def c_sell(self, source, type, name):
        if type == 'frame' or type == 'voiceline':
            self.bot.request_manager.create_request(SellRequest(source.author.id, self.bot, type, name))
        else:
            await self.bot.send_message(
                source.channel, '```Are you sure you want to sell %s %s? ($confirm or $cancel)```' % type, name)

    @command(context=PRIVATE, access=USER, types=())
    async def c_confirm(self, source):
        try:
            self.bot.request_manager.confirm_request(source.author.id)
        except BotRequestException as e:
            await self.bot.send_message(source.channel, '```%s```' % e.message)

    @command(context=PRIVATE, access=USER, types=())
    async def c_cancel(self, source):
        try:
            self.bot.request_manager.cancel_request(source.author.id)
        except BotRequestException as e:
            await self.bot.send_message(source.channel, '```%s```' % e.message)

    @command(context=PRIVATE, access=USER, types=())
    async def c_undo(self, source):
        try:
            self.bot.request_manager.undo_request(source.author.id)
        except BotRequestException as e:
            await self.bot.send_message(source.channel, '```%s```' % e.message)

    @command(context=PRIVATE, access=USER, types=(str, str, str))
    async def c_rename(self, source, type, from_name, to_name):
        # Get the user data
        user = self.bot.userdb.get(source.author.id)
        if user is None or len(user.inventory) == 0:
            await self.bot.send_message(source.channel, '```You do not own any items to rename.```')
            return

        # Get the voice line from the name
        try:
            item_to_rename = [item for item in user.inventory if item.name == from_name and item.type == type][0]
        except IndexError:
            await self.bot.send_message(source.channel, '```You do not own a %s named %s.```' % (type, from_name))
            return

        # Rename item
        item_idx = user.inventory.index(item_to_rename)
        item_to_rename.name = to_name
        user.inventory[item_idx] = item_to_rename
        # Update user in the database
        self.bot.userdb.update({'$set': user.as_document()})
        await self.bot.send_message(
            source.channel, '```Successfully renamed %s from %s to %s.```' % (type, from_name, to_name))

    @command(context=BOTH, access=ADMIN, types=(str, int, int))
    async def c_points(self, source, type, amount, target_id):
        # Get the user data
        if target_id == 0:
            target_id = source.author.id
        user = self.bot.userdb.get(target_id)

        if user is None:
            await self.bot.send_message(source.channel, '```Invalid user.```')
            return

        if type == 'add':
            user.total_points += amount
            user.current_points += amount
            await self.bot.send_message(source.channel, 'Adding %s point(s) to **%s**.' % (amount, source.author.name))
        elif type == 'remove':
            user.total_points -= amount
            user.current_points -= amount
            await self.bot.send_message(source.channel, 'Removing %s point(s) from **%s**.' % (amount, source.author.name))
        else:
            await self.bot.send_message(source.channel, 'Invalid use of **points** command.')
            return

        self.bot.userdb.update(user, {'$set': user.as_document()})


    async def invalid_arguments(self, source, command_name):
        await self.bot.send_message(source.channel, '```Invalid arguments to command %s.```' % command_name)

    async def invalid_context(self, source, command_name, context):
        if context == PUBLIC:
            await self.bot.send_message(source.channel,
                                        '```The command %s can only be used in a server text channel.```' % command_name)
            return
        if context == PRIVATE:
            await self.bot.send_message(source.channel,
                                        '```The command %s can only be used in a private message.```' % command_name)
            return

    async def invalid_access(self, source, command_name, access):
        await self.bot.send_message(source.channel,
                                    '```You do not have sufficient access to use the command %s.```' % command_name)
