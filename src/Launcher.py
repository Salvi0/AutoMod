# force the bot to use v6 since d.py uses v7 which can cause problems
import discord.http
discord.http.Route.BASE = "https://discordapp.com/api/v6"

from Bot.AutoMod import AutoMod
from discord import Intents
from Database import Connector, DBUtils

from Utils import Logging

import logging
from logging.handlers import RotatingFileHandler

import contextlib
import datetime
import asyncio
import traceback
import argparse

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


db = Connector.Database()


def prefix_callable(bot, message):
    prefixes = [f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "]
    if message.guild is None:
        prefixes.append("+")
    elif bot.READY:
        try:
            prefix = DBUtils.get(db.configs, "guildId", f"{message.guild.id}", "prefix")
            if prefix is not None:
                prefixes.append(prefix)
            else:
                prefixes.append("+")
        except Exception:
            prefixes.append("+")
    return prefixes


class LogFilter(logging.Filter):
    def __init__(self):
        super().__init__(name="discord.state")
    
    def filter(self, r):
        if r.levelname == "WARNING" and "referencing an unknown" in r.msg:
            return False
        return True


@contextlib.contextmanager
def init_logger():
    try:
        max_bytes = 32 * 1024 * 1012
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
        logging.getLogger("discord.state").addFilter(LogFilter())

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = RotatingFileHandler(filename="automod.log", encoding="utf-8", mode="w", maxBytes=max_bytes, backupCount=5)
        fmt = "%d/%M/%Y %H:%M:%S"
        formatter = logging.Formatter("[{asctime}] [{levelname:<7}] {name}: {message}", fmt, style="{")
        handler.setFormatter(formatter)
        log.addHandler(handler)

        yield
    finally:
        handlers = log.handlers[:]
        for _handler in handlers:
            _handler.close()
            log.removeHandler(_handler)



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--total_shards", help="The total amount of shards to use")
    cl_args = p.parse_args()

    args = {
        "command_prefix": prefix_callable,
        "case_insensitive": True,
        "max_messages": 1000,
        "intents": Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            messages=True,
            reactions=True
        ),
        "chunk_guilds_at_startup": False,
        "description": "Discord moderation/utility bot!"
    }

    if cl_args.total_shards:
        shard_count = int(cl_args.total_shards)
        args.update({
            "shard_count": shard_count
        })
    
    with init_logger():
        automod = AutoMod(**args)
        automod.remove_command("help")
        automod.run()