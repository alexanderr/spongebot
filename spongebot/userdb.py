import time

import pymongo
from discord.user import User


def get_user_id(user):
    if isinstance(user, User) or issubclass(user.__class__, User):
        return user.id
    elif isinstance(user, SpongebotUser):
        return user.as_document()['_id']
    else:
        return user


class UserMongoDB:
    def __init__(self, bot):
        self.bot = bot

        url = self.bot.config.get('mongodb_url', 'mongodb://localhost')

        self.bot.log('Connecting to MongoDB database at %s...' % url)

        self.mongo = pymongo.MongoClient(host=url)

        self.mongodb = self.mongo['spongebot']
        self.userdb = self.mongodb['users']

    def insert(self, user):
        user_id = get_user_id(user)
        spongebot_user = SpongebotUser()
        spongebot_user._id = user_id
        spongebot_user.name = user.name
        spongebot_user.create_date = int(time.time())
        self.userdb.insert_one(spongebot_user.as_document())

    def get(self, user):
        user_id = get_user_id(user)

        document = self.userdb.find_one({'_id': user_id})
        if document is None:
            return None

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
        self.name = ''
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
        documented_inv = [item.as_document() for item in self.inventory]
        documented_lsi = self.last_sold_item
        if self.last_sold_item is not None:
            documented_lsi = self.last_sold_item.as_document()
        document = self.__dict__.copy()
        document['inventory'] = documented_inv
        document['last_sold_item'] = documented_lsi
        return document

    def from_document(self, document):
        undocumented_inventory = []
        for doc in document['inventory']:
            if doc['item_type'] == 'frame':
                item = FrameInventoryItem(0, 0, 0, 0, 0)
            elif doc['item_type'] == 'voiceline':
                item = VoicelineInventoryItem(0, 0, 0, 0, 0)
            else:
                continue
            item.from_document(doc)
            undocumented_inventory.append(item)
        undocumented_lsi = None
        if document.get('last_sold_item'):
            item = None
            if document['last_sold_item']['item_type'] == 'frame':
                item = FrameInventoryItem(0, 0, 0, 0, 0)
            elif document['last_sold_item']['item_type'] == 'voiceline':
                item = VoicelineInventoryItem(0, 0, 0, 0, 0)
            if item is not None:
                item.from_document(document['last_sold_item'])
                undocumented_lsi = item
        document['inventory'] = undocumented_inventory
        document['last_sold_item'] = undocumented_lsi
        self.__dict__.update(document)


class InventoryItem:
    def __init__(self, item_type, date_received):
        self.item_type = item_type
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
