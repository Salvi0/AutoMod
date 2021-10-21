import datetime
import traceback
import discord
import asyncio
import threading

from plugins.Types import Embed



class ActionLogger:
    def __init__(self, bot):
        self.bot = bot
        self.i18next = bot.i18next
        self.log_configs = {
            "ban": {
                "channel": "mod_log",
                "key": "log_ban",
                "on_time": True,
                "color": 0xff5c5c,
                "emote": "HAMMER"
            },
            "kick": {
                "channel": "mod_log",
                "key": "log_kick",
                "on_time": True,
                "color": 0xf79554,
                "emote": "SHOE"
            },
            "forceban": {
                "channel": "mod_log",
                "key": "log_forceban",
                "on_time": True,
                "color": 0xff5c5c,
                "emote": "HAMMER"
            },
            "softban": {
                "channel": "mod_log",
                "key": "log_softban",
                "on_time": True,
                "color": 0xf79554,
                "emote": "HAMMER"
            },
            "restrict": {
                "channel": "mod_log",
                "key": "log_restrict",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "RESTRICT"
            },
            "unban": {
                "channel": "mod_log",
                "key": "log_unban",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "UNLOCK"
            },
            "manual_unban": {
                "channel": "mod_log",
                "key": "log_manual_unban",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "UNLOCK"
            },
            "cybernuke": {
                "channel": "mod_log",
                "key": "log_cybernuke",
                "on_time": True,
                "color": 0x4569e1,
                "emote": "HAMMER"
            },

            "mute": {
                "channel": "mod_log",
                "key": "log_mute",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "MUTE"
            },
            "mute_extended": {
                "channel": "mod_log",
                "key": "log_mute_extended",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "MUTE"
            },
            "unmute": {
                "channel": "mod_log",
                "key": "log_unmute",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "UNMUTE"
            },
            "manual_unmute": {
                "channel": "mod_log",
                "key": "log_manual_unmute",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "UNMUTE"
            },

            "warn": {
                "channel": "mod_log",
                "key": "log_warn",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "WARN"
            },

            "voice_join": {
                "channel": "voice_log",
                "key": "voice_channel_join",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "BLUEDOT"
            },
            "voice_leave": {
                "channel": "voice_log",
                "key": "voice_channel_leave",
                "on_time": True,
                "color": 0xff5c5c,
                "emote": "REDDOT"
            },
            "voice_switch": {
                "channel": "voice_log",
                "key": "voice_channel_switch",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "SWITCH"
            },

            "message_deleted": {
                "channel": "message_log",
                "key": "log_message_deletion",
                "on_time": True,
                "color": 0xff5c5c,
                "emote": "BIN"
            },
            "message_edited": {
                "channel": "message_log",
                "key": "log_message_edit",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "PEN"
            },

            "member_join": {
                "channel": "server_log",
                "key": "log_join",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "JOIN"
            },
            "member_leave": {
                "channel": "server_log",
                "key": "log_leave",
                "on_time": True,
                "color": 0xff5c5c,
                "emote": "LEAVE"
            },
            "member_join_cases": {
                "channel": "server_log",
                "key": "log_join_with_prior_cases",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "WARN"
            },

            "warns_added": {
                "channel": "mod_log",
                "key": "log_warns_added",
                "on_time": True,
                "color": 0xffdc5c,
                "emote": "WARN"
            },

            "unwarn": {
                "channel": "mod_log",
                "key": "log_unwarn",
                "on_time": True,
                "color": 0x5cff9d,
                "emote": "ANGEL"
            },

            "raid_on": {
                "channel": "mod_log",
                "key": "log_raid_on",
                "on_time": True,
                "color": 0x202225,
                "emote": "LOCK"
            },
            "raid_off": {
                "channel": "mod_log",
                "key": "log_raid_off",
                "on_time": True,
                "color": 0x202225,
                "emote": "UNLOCK"
            }
        }


    async def log(self, guild, log_type, **kwargs):
        if not log_type in self.log_configs:
            raise Exception("Invalid log type")
        
        conf = self.log_configs[log_type]

        log_channel_id = self.bot.db.configs.get(guild.id, conf["channel"])
        if log_channel_id == None or log_channel_id == "":
            return
        
        log_channel = await self.bot.utils.getChannel(guild, log_channel_id)
        if log_channel is None:
            return

        log_key = conf["key"]
        log_emote = conf["emote"]
        if conf["on_time"]:
            kwargs.update({
                "on_time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })

        if kwargs.get("_embed") is None:
            e = Embed(
                color=conf["color"],
                timestamp=datetime.datetime.utcnow()
            )

            if kwargs.get("moderator") is None:
                kwargs.update({"moderator": guild.me, "moderator_id": guild.me.id})

            e.set_author(
                name=f"{kwargs.get('moderator')} ({kwargs.get('moderator_id')})", 
                icon_url=(kwargs.get("moderator")).display_avatar
            )

            if "user" in kwargs:
                if not isinstance(kwargs.get("user"), str):
                    e.set_thumbnail(
                        url=(kwargs.get("user")).display_avatar
                    )

            dm = kwargs.get("dm", None)
            if dm is not None:
                if "failed" in dm:
                    dm = " | No DM sent"
                elif dm == "":
                    dm = " | No DM sent"
                else:
                    dm = " | DM sent"

            if "case" in kwargs:
                e.set_footer(
                    text=f"Case #{kwargs.get('case')}{dm if dm is not None else ''}"
                )
                
            e.description = self.i18next.translate(guild, log_key, _emote=log_emote, **kwargs)
        else:
            e = kwargs.get("_embed")

        try:
            log_message = await log_channel.send(content=kwargs.get("content", None), embed=e)
        except Exception:
            pass
        else:
            if "case" in kwargs:
                self.bot.db.inf.update(f"{guild.id}-{kwargs.get('case')}", "log_id", f"{log_message.id}")
                self.bot.db.inf.update(f"{guild.id}-{kwargs.get('case')}", "jump_url", f"{log_message.jump_url}")