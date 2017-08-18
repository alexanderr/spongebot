class BotRequest:
    # Used to allow confirmations for bot commands

    S_PENDING = 0
    S_COMPLETED = 1
    S_CANCELED = 2
    S_REVERTED = 3

    def __init__(self, requester, bot):
        self.requester = requester
        self.bot = bot
        self._state = self.S_PENDING

    def confirm(self):
        if self._state != self.S_PENDING:
            raise BotRequestException('Failed to confirm request.')
        self._state = self.S_COMPLETED

    def cancel(self):
        if self._state != self.S_PENDING:
            raise BotRequestException('Failed to cancel request.')
        self._state = self.S_CANCELED

    def undo(self):
        if self._state != self.S_COMPLETED:
            raise BotRequestException('Failed to undo request.')
        self._state = self.S_REVERTED


class SellRequest(BotRequest):
    def __init__(self, requester, bot, item_type, item_name):
        BotRequest.__init__(self, requester, bot)
        self.item_type = item_type
        self.item_name = item_name

    def confirm(self):
        BotRequest.confirm(self)
        # Get item in question
        data = self.bot.userdb.get(self.requester)
        if data is None or len(data.inventory) == 0:
            raise BotRequestException('No items to sell.')
        item = [item for item in data.inventory if item.item_type == self.item_type and item.name == self.item_name][0]
        # Remove item from inventory
        data.inventory.remove(item)
        # Put item_id in sold items
        data.last_sold_item = item
        # Give money back
        data.current_points += 15
        # Update user entry
        self.bot.userdb.update(self.requester, {'$set': data.as_document()})

    def undo(self):
        BotRequest.undo(self)
        # Get last sold item
        data = self.bot.userdb.get(self.requester)
        if data is None or data.current_points < 15:
            # Cannot purchase that item back
            raise BotRequestException('Not enough funds.')
        item = data.last_sold_item
        # Add item back to inventory
        data.inventory.add(item)
        # Remove item_id from last sold item
        data.last_sold_item = None
        # Take money back
        data.current_points -= 15
        # Update user entry
        self.bot.userdb.update(self.requester, {'$set': data.as_document()})


class BotRequestException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message