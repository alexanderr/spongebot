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

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.authenticate())
    except KeyboardInterrupt:
        print('Exiting...')
    except Exception as e:
        print(type(e))
        raise e

    loop.run_until_complete(bot.logout())
    for task in asyncio.Task.all_tasks():
        task.cancel()

    if not loop.is_closed():
        asyncio.ensure_future(loop.stop())

