import sys

import discord

from spongebot.spongebot import Spongebot


if sys.platform.startswith('win'):
    # use the Proactor event loop on Windows
    import asyncio
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


bot = Spongebot()
bot.setup_logging()
bot.load_config()
bot.parse_episode_data()

discord.opus.load_opus(bot.config['opus_path'])
bot.run(bot.config['username'], bot.config['password'])
