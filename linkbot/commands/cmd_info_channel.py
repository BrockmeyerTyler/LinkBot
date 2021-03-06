import linkbot.utils.queries.infochannel as queries
from linkbot.utils.cmd_utils import *
from linkbot.utils.search import search_channels, resolve_search_results


async def get_guild_info_channel(guild: discord.Guild):
    async with await db.Session.new() as sess:
        channel_id = await queries.get_info_channel(sess, guild.id)
    return guild.get_channel(channel_id) if channel_id else guild.system_channel


@command([], "", [], name='infochan', show_in_help=False, help_subcommand=False)
@restrict(ADMIN_ONLY)
async def info_channel(cmd: Command):

    async def set_channel(c):
        nonlocal channel
        channel = c

    if not cmd.args:
        async with await db.Session.new() as sess:
            channel_id = await queries.get_info_channel(sess, cmd.guild.id)
        if channel_id:
            await cmd.channel.send(embed=bot.embed(
                c=discord.Color.blurple(),
                title=f"Info channel for {cmd.guild.name}\n"
                      f"{emoji.Symbol.information_source} #{cmd.guild.get_channel(channel_id).name}"))
        else:
            raise CommandError(cmd, "There is currently no registered information channel.")

    else:
        channel = None
        results = search_channels(cmd.argstr, cmd.guild, 't')
        await resolve_search_results(results, cmd.argstr, 'channels', cmd.author, cmd.channel, set_channel)
        if not channel:
            return
        async with await db.Session.new() as sess:
            await queries.set_info_channel(sess, cmd.guild.id, channel.id)
        await send_success(cmd.message)
