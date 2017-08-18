import random
import time
import asyncio

from spongebot.crate import FrameCrate, VoicelineCrate
from spongebot.constants import CRATE_PRICE
from spongebot.userdb import FrameInventoryItem, VoicelineInventoryItem


class CrateManager:
    def __init__(self, bot):
        self.bot = bot
        self.crate_queue = []
        self.generated_crate_queue = []

    def initialize_tasks(self):
        self.bot.loop.create_task(self.generate_crate_task())
        self.bot.loop.create_task(self.deliver_crate_task())

    async def generate_crate(self, source):
        data = self.bot.userdb.get(source.author)
        if data is None:
            await self.bot.send_message(source.channel, '```You need at least 30 points to open a crate.```')
            return

        if data.current_points < CRATE_PRICE:
            await self.bot.send_message(source.channel, '```You need at least 30 points to open a crate.```')
            return

        self.bot.log('Generating crate type...')

        rng = random.random()
        random.seed(str(time.time()) + str(source.author.id) + str(id(self)))

        if rng < .33:
            crate = VoicelineCrate(source.author.id, source.channel)
            crate_field = 'voiceline_id'
        else:
            crate = FrameCrate(source.author.id, source.channel)
            crate_field = 'frame_id'

        self.bot.userdb.update(source.author, {'$inc': {'crates_opened': 1, 'current_points': -30, crate_field: 1}})

        data = self.bot.userdb.get(source.author)

        if isinstance(crate, FrameCrate):
            crate.crate_id = data.frame_id
        elif isinstance(crate, VoicelineCrate):
            crate.crate_id = data.voiceline_id

        await self.bot.send_message(source.channel, '```Opening a crate for you... This might take a few seconds...```')

        self.bot.log('Adding crate type %s to queue for %s...' % (crate.__class__.__name__, crate.user_id))

        self.crate_queue.append(crate)

    async def generate_crate_task(self):
        while not self.bot.is_closed:
            if len(self.crate_queue):
                crate = self.crate_queue.pop(0)
                self.bot.log('Generating crate for %s...' % crate.user_id)
                future = self.bot.loop.run_in_executor(None,
                                                       crate.generate, self)
                await future

            await asyncio.sleep(1, loop=self.bot.loop)

    async def deliver_crate_task(self):
        while not self.bot.is_closed:
            if len(self.generated_crate_queue):
                crate = self.generated_crate_queue.pop(0)
                # Get user's db data
                user = self.bot.userdb.get(crate.user_id)

                self.bot.log('Delivering crate for %s...' % crate.user_id)

                await self.bot.send_message(crate.channel, '```Crate opened!```')

                if isinstance(crate, FrameCrate):
                    # Add crate item to user inventory
                    user.inventory.append(FrameInventoryItem('frame', time.time(), crate.crate_id, crate.crate_id, crate.episode))
                    # Update user db
                    self.bot.userdb.update(crate.user_id, {'$set': user.as_document()})
                    await self.bot.send_message(crate.channel, '```You got a Frame Crate!```')

                    with open(crate.frame, 'rb') as fb:
                        await self.bot.send_file(crate.channel, fb)

                elif isinstance(crate, VoicelineCrate):
                    # Add crate item to user inventory
                    user.inventory.append(VoicelineInventoryItem('voiceline', time.time(), crate.crate_id, crate.crate_id, crate.episode))
                    # Update user db
                    self.bot.userdb.update(crate.user_id, {'$set': user.as_document()})
                    await self.bot.send_message(crate.channel, '```You got a Voiceline Crate!```')
                    await self.bot.send_message(
                        crate.channel,
                        'You can play your new voiceline by using the ```$voiceline %d``` command in the server chat.'
                        % crate.crate_id)

            await asyncio.sleep(1, loop=self.bot.loop)
