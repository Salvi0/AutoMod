import discord
from discord.ext import commands

import logging; log = logging.getLogger(__name__)
import requests
import datetime
import traceback
import sys
from discord.ext.commands.flags import F
from toolbox import S

from i18n.Translator import Translator
from services.Database import MongoDB, MongoSchemas
from services.Caching import Cache
from services.ActionLogger import ActionLogger
from services.IgnoreForEvent import IgnoreForEvent
from services.ActionValidator import ActionValidator
from data.Emotes import Emotes
from utils.ModifyConfig import ModifyConfig
from utils.BotUtils import BotUtils
from plugins.Types import Embed
from utils.HelpUtils import getHelpForPlugin
from utils.Context import Context



def _prefix_callable(bot, message):
    base = [f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "]
    if message.guild is None:
        base.append(bot.config.default_prefix)
    elif not bot.locked:
        try:
            prefix = bot.db.configs.get(message.guild.id, "prefix")
            base.append(prefix)
        except Exception:
            base.append(bot.config.default_prefix)
    
    for p in base: 
        if p == None:
            base.remove(p)
    return base


class AutoMod(commands.AutoShardedBot):
    def __init__(self, config: dict):
        self.config = config = S(config)
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            messages=True,
            reactions=True,
            voice_states=True,
            typing=False
        )
        super().__init__(
           command_prefix=_prefix_callable, intents=intents, case_insensitive=True, 
           max_messages=1000, chunk_guilds_at_startup=False, shard_count=config.shards,
           allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False)
        )
        self.ready = False
        self.locked = True

        self.active_chunk = False
        self.pending_chunk = False
        self.terminate_chunk = False

        self.used_commands = 0
        self.used_tags = 0
        self.total_shards = config.shards
        self.version = None
        self.case_cache = {}
        self.command_stats = {}

        self.i18next = Translator(self, config.langs)
        db_name = config.mongo_url.split("net/")[1].split("?")[0]
        self.db = MongoDB(
            host=config.mongo_url, 
            _name=db_name if db_name != "" else "main"
        ).database
        self.schemas = MongoSchemas(self)
        self.cache = Cache(self)
        self.emotes = Emotes(self)
        self.action_logger = ActionLogger(self)
        self.ignore_for_event = IgnoreForEvent(self)
        self.action_validator = ActionValidator(self)
        self.utils = BotUtils(self)
        self.modify_config = ModifyConfig(self)

        if not hasattr(self, "uptime"):
            self.uptime = datetime.datetime.utcnow()
        self.remove_command("help")

        for plugin in self.config.plugins:
            try:
                self.load_extension("plugins.{}".format(plugin))
                log.info("Loaded {}".format(plugin))
            except Exception as ex:
                log.warning("Failed to load {} - {}".format(plugin, ex))

        self.run()

    def dispatch(self, event_name, *args, **kwargs):
        super().dispatch(event_name, *args, **kwargs)
        if event_name == "message":
            super().dispatch("tags_event", *args, **kwargs)
            super().dispatch("automod_event", *args, **kwargs)
            super().dispatch("filter_event", *args, **kwargs)
            #super().dispatch("stats_event", *args, **kwargs)
    
    
    async def on_ready(self):
        if self.config.custom_status != "":
            if self.activity is None:
                await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=self.config.custom_status))
        for guild in self.guilds:
            if not self.db.configs.exists(f"{guild.id}"):
                self.db.configs.insert(self.schemas.GuildConfig(guild))
                log.info("Filled up missing guild {} ({})".format(guild.name, guild.id))

        self.ready = True
        self.locked = False


    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        ctx = await self.get_context(message, cls=Context) # TODO: fix this
        if ctx.valid and ctx.command is not None:
            if not ctx.command.qualified_name in self.command_stats:
                self.command_stats.update({
                    ctx.command.qualified_name: 1
                })
            else:
                self.command_stats[ctx.command.qualified_name] += 1
            if self.ready:
                if not message.guild.chunked:
                    await message.guild.chunk(cache=True)
            
            await self.invoke(ctx)


    async def on_interaction(self, i: discord.Interaction):
        if i.type == discord.InteractionType.component:
            _id = i.data.get("custom_id")
            if _id.startswith("help:"):
                selected = i.data.get("values")[0]
                selected = selected if selected != "None" else None
                embed, view = await getHelpForPlugin(self, selected, i)
                try:
                    await i.response.edit_message(
                        embed=embed, 
                        view=view
                    )
                except discord.NotFound:
                    try:
                        await i.delete_original_message()
                    except Exception:
                        pass
                    finally:
                        await i.channel.send("Invalid interaction, please use the command again.")

    
    async def on_error(self, event, *args, **kwargs):
        error = sys.exc_info()
        e = Embed(
            color=0xff5c5c,
            title="Event Error",
            description="```py\n{}\n```".format("".join(
                traceback.format_exception(
                    etype=error[0], 
                    value=error[1], 
                    tb=error[2]
                )
            ))
        )
        e.add_field(
            name="❯ Event",
            value=f"{event}",
            inline=True
        )
        if len(args) > 0:
            try:
                guild = args[0].guild or args[0]
            except Exception:
                guild = None
        else:
            guild = None
        e.add_field(
            name="❯ Location",
            value="• Name: {} \n• ID: {}".format(
                guild.name if guild != None else "None",
                guild.id if guild != None else "None"
            ),
            inline=True
        )
        await self.utils.sendErrorLog(e)

    
    def get_uptime(self, display_raw=False):
        raw = datetime.datetime.utcnow() - self.uptime
        hours, remainder = divmod(int(raw.total_seconds()), 3600)
        days, hours = divmod(hours, 24)
        minutes, seconds = divmod(remainder, 60)
        if display_raw:
            return days, hours, minutes, seconds
        else:
            return "{}d, {}h, {}m & {}s".format(days, hours, minutes, seconds)


    def get_shard_ping(self, guild, ndigits=2):
        ping = round([x for i, x in self.shards.items() if i == guild.shard_id][0].latency * 1000, ndigits)
        return ping


    def get_guild_prefix(self, guild):
        prefix = self.db.configs.get(guild.id, "prefix")
        return prefix

    
    def handle_timeout(self, mute, guild, user, ios8601_ts):
        exc = ""
        try:
            resp = requests.patch(
                f"https://discord.com/api/v9/guilds/{guild.id}/members/{user.id}",
                json={
                    "communication_disabled_until": None if mute == False else ios8601_ts
                }, 
                headers={
                    "Authorization": f"Bot {self.config.token}"
                }
            )
            if resp.status_code != 200: exc = resp.text
        except Exception as ex:
            log.warn(f"Error while trying to mute user ({user.id}) (guild: {guild.id}) - {ex}"); exc = ex
        finally:
            return exc


    def run(self):
        try:
            super().run(self.config.token)
        finally:
            pass