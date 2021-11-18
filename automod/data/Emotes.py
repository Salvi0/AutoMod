import json
import logging; log = logging.getLogger(__name__)
import pathlib



class Emotes:
    def __init__(self, bot):
        self.bot = bot
        with open(f"{pathlib.Path(__file__).parent}/emotes.json", "r", encoding="utf8", errors="ignore") as f:
            self.emotes = json.load(f)
            if bot.config.dev:
                self.emotes.update({
                    "YES": "<:yes:880522968969658448>", #👌
                    "NO": "<:no:880522968952872990>" #❌
                })


    def get(self, key):
        try:
            return self.emotes[key]
        except KeyError:
            log.warn("Failed to obtain an emoji with key {}".format(key))


    def reload(self):
        with open(f"{pathlib.Path(__file__).parent}/emotes.json", "r", encoding="utf8", errors="ignore") as f:
            self.emotes = json.load(f)
            if self.bot.config.dev:
                self.emotes.update({
                    "YES": "👌",
                    "NO": "❌"
                })