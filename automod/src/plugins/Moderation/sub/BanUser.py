from ....utils import Permissions



async def banUser(plugin, ctx, user, reason, log_type, ban_type, days=0):
    try:
        if await Permissions.is_banned(ctx, user):
            return await ctx.send(plugin.i18next.t(ctx.guild, "target_already_banned", _emote="WARN"))
        await ctx.guild.ban(user, reason=reason, delete_message_days=days)
    except Exception as ex:
        return await ctx.send(plugin.i18next.t(ctx.guild, "ban_failed", _emote="NO", error=ex))
    else:
        plugin.bot.ignore_for_event.add("bans_kicks", user.id)
        case = plugin.bot.utils.newCase(ctx.guild, log_type.capitalize(), user, ctx.author, reason)
        dm_result = await plugin.bot.utils.dmUser(ctx.message, log_type, user, _emote="HAMMER", guild_name=ctx.guild.name, reason=reason)
        await ctx.send(plugin.i18next.t(ctx.guild, f"user_{ban_type}", _emote="YES", user=user, reason=reason, case=case))

        await plugin.action_logger.log(
            ctx.guild, 
            log_type, 
            moderator=ctx.message.author, 
            moderator_id=ctx.message.author.id,
            user=user,
            user_id=user.id,
            reason=reason,
            case=case,
            dm=dm_result
        )