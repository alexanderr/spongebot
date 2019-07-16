import sys

if sys.version_info < (3, 5):
    print('Python 3.5 is required to run spongebot. Exiting...')
    sys.exit(0)

import discord
import os


from spongebot.spongebot import Spongebot


if sys.platform.startswith('win'):
    # use the Proactor event loop on Windows
    import asyncio
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)

subfolders = ['content', 'frames', 'voicelines', 'logs', 'users']

for folder in subfolders:
    if not os.path.exists(folder):
        os.mkdir(folder)


bot = Spongebot()
bot.load_config()
bot.parse_episode_data()

discord.opus.load_opus(bot.config['opus_path'])
bot.run(bot.config['secret'])
