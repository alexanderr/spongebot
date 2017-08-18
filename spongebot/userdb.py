import time

import pymongo
from discord.user import User


def get_user_id(user):
    if isinstance(user, User) or issubclass(user.__class__, User):
        return user.id
    if isinstance(user, SpongebotUser):
        return user.as_document()['_id']
    else:
        return user


class UserMongoDB:
    def __init__(self, bot):
        self.bot = bot

        url = self.bot.config.get('mongodb_url', 'mongodb://localhost')

        self.mongo = pymongo.MongoClient(host=url)

        self.mongodb = self.mongo['spongebot']
        self.userdb = self.mongodb['users']

    def insert(self, user):
        user_id = get_user_id(user)
        spongebot_user = SpongebotUser()
        spongebot_user._id = user_id
        spongebot_user.create_date = int(time.time())
        self.userdb.insert_one(spongebot_user.as_document())

    def get(self, user):
        user_id = get_user_id(user)

        document = self.userdb.find_one({'_id': user_id})

        spongebot_user = SpongebotUser()
        spongebot_user.from_document(document)

        return spongebot_user

    def update(self, user, new):
        user_id = get_user_id(user)
        self.userdb.update_one({'_id': user_id}, new)

    def exists(self, user):
        user_id = get_user_id(user)

        return self.userdb.find_one({'_id': user_id}) is not None


class SpongebotUser:
    def __init__(self):
        self._id = 0
        self.user_name = ''
        self.create_date = 0
        self.access_level = 0
        self.current_points = 0
        self.total_points = 0
        self.crates_opened = 0
        self.frame_id = 0
        self.voiceline_id = 0
        self.episodes_watched = 0
        self.episode_list = []
        self.inventory = []
        self.last_sold_item = None

    def as_document(self):
        return self.__dict__

    def from_document(self, document):
        self.__dict__.update(document)


class InventoryItem:
    def __init__(self, type, date_received):
        self.type = type
        self.date_received = date_received

    def as_document(self):
        return self.__dict__

    def from_document(self, document):
        self.__dict__.update(document)


class FrameInventoryItem(InventoryItem):
    def __init__(self, item_type, date_received, name, idx, from_episode):
        InventoryItem.__init__(self, item_type, date_received)
        self.name = name
        self.idx = idx
        self.from_episode = from_episode


class VoicelineInventoryItem(InventoryItem):
    def __init__(self, item_type, date_received, name, idx, from_episode):
        InventoryItem.__init__(self, item_type, date_received)
        self.name = name
        self.idx = idx
        self.from_episode = from_episode
