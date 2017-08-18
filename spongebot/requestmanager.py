from spongebot.botrequest import BotRequestException


class RequestManager:
    def __init__(self, bot):
        self.bot = bot
        self.user_requests = {}

    def create_request(self, request):
        self.user_requests[request.requester] = request

    def confirm_request(self, user_id):
        try:
            return self.user_requests[user_id].confirm()
        except KeyError:
            raise BotRequestException('No request to confirm.')

    def cancel_request(self, user_id):
        try:
            msg = self.user_requests[user_id].cancel()
            del self.user_requests[user_id]
            return msg
        except KeyError:
            raise BotRequestException('No request to cancel.')

    def undo_request(self, user_id):
        try:
            return self.user_requests[user_id].undo()
        except KeyError:
            raise BotRequestException('No request to undo.')