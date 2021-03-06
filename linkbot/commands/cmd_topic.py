import linkbot.utils.queries.management as management_queries
import linkbot.utils.queries.topic as queries
from linkbot.utils.cmd_utils import *


# TODO: Turn topics into groups
# groups:
#   can be created, public or private for viewing and joining.
#     private viewing means that only those that are in the group can see it or use it.
#     private joining means that people other than the creator must be invited to the group to join it.
#     a group with private viewing also has private joining.
#   not locked to guilds
#   allow for inviting others in, join via reactions.
#   Can be used to mention all people in the group, send a group-wide message, etc.
#   And more!
#   All current features of topics should be adopted by groups.

@command(
    [
        '{c} list',
        '{c} create <topic>',
        '{c} delete <topic>',
        '{c} subscribe <topic>',
        '{c} unsubscribe <topic>',
        '{c} subscriptions',
        '{c} @ <topic>'
    ],
    "Create topics that members can subscribe to. Ping the subscribers of a topic when you have something to share.",
    [
        ("{c} list", "Displays all topics that are available on this server."),
        ("{c} create Rocket League", "Creates a topic called Rocket League."),
        ("{c} delete Rocket League", "Deletes a topic called Rocket League."),
        ("{c} subscribe Politics", "Subscribe yourself to the topic of Politics."),
        ("{c} unsubscribe Politics", "Unsubscribe yourself from the Politics topic."),
        ("{c} subscriptions", "List all of your subscriptions for the current guild."),
        ("{c} @ Coding", "Mention all members who are subscribed to the Coding topic.")
    ],
    aliases=['topics']
)
@require_args(1)
@restrict(SERVER_ONLY)
async def topic(cmd: Command):
    subarg = cmd.args[0].lower()
    cmd.shiftargs()
    if subarg == 'list':
        await topic_list(cmd)
    elif subarg in ['create', 'add']:
        await topic_create(cmd)
    elif subarg in ['delete', 'remove']:
        await topic_delete(cmd)
    elif subarg in ['sub', 'subscribe']:
        await topic_subscribe(cmd)
    elif subarg in ['unsub', 'unsubscribe']:
        await topic_unsubscribe(cmd)
    elif subarg in ['subs', 'subscriptions']:
        await topic_subscriptions(cmd)
    elif subarg in ['@', 'ping']:
        await topic_ping(cmd)
    else:
        raise CommandSyntaxError(cmd, f"Unknown sub argument '{subarg}'")


async def topic_list(cmd: Command):
    async with await db.Session.new() as sess:
        results = await queries.get_guild_topics(sess, cmd.guild.id)
    if not results:
        raise CommandError(cmd, f"No one has created any topics for {cmd.guild.name}.")
    await cmd.channel.send(embed=bot.embed(
        c=discord.Color.teal(),
        title="Topics",
        description="\n".join(f"**{name}**: {count} subs" for name, count in results)))


@require_args(1)
async def topic_create(cmd: Command):
    async with await db.Session.new() as sess:
        result = await queries.get_topic(sess, cmd.guild.id, cmd.argstr)
        if result:
            raise CommandError(cmd, f"A topic named '{cmd.argstr}' already exists.")
        await queries.create_topic(sess, cmd.guild.id, cmd.argstr)
    await send_success(cmd.message)


@restrict(ADMIN_ONLY)
@require_args(1)
async def topic_delete(cmd: Command):
    async with await db.Session.new() as sess:
        result = await queries.get_topic(sess, cmd.guild.id, cmd.argstr)
        if not result:
            raise CommandError(cmd, f"No topic named '{cmd.argstr}' exists.")
        await management_queries.delete_node_with_id(sess, result[0])
    await send_success(cmd.message)


@require_args(1)
async def topic_subscribe(cmd: Command):
    async with await db.Session.new() as sess:
        result = await queries.get_topic(sess, cmd.guild.id, cmd.argstr)
        if not result:
            raise CommandError(cmd, f"No topic named '{cmd.argstr}' exists.")
        await queries.create_sub_to_topic(sess, cmd.guild.id, cmd.author.id, cmd.argstr)
    await send_success(cmd.message)


@require_args(1)
async def topic_unsubscribe(cmd: Command):
    async with await db.Session.new() as sess:
        result = await queries.get_topic(sess, cmd.guild.id, cmd.argstr)
        if not result:
            raise CommandError(cmd, f"No topic named '{cmd.argstr}' exists.")
        await queries.delete_sub_to_topic(sess, cmd.guild.id, cmd.author.id, cmd.argstr)
    await send_success(cmd.message)


async def topic_subscriptions(cmd: Command):
    async with await db.Session.new() as sess:
        results = await queries.get_member_subscriptions(sess, cmd.guild.id, cmd.author.id)
    if not results:
        raise CommandError(cmd, "You are not subscribed to any topics.")
    await cmd.channel.send(embed=bot.embed(
        c=discord.Color.teal(),
        title=f"Your Topic Subscriptions for {cmd.guild.name}",
        description="\n".join(results)))


async def topic_ping(cmd: Command):
    async with await db.Session.new() as sess:
        results = await queries.get_topic_subs(sess, cmd.guild.id, cmd.argstr)
    if not results:
        raise CommandError(cmd, "Either the topic does not exist, or there are no subscribers.")
    await cmd.channel.send(" ".join(cmd.guild.get_member(r).mention for r in results), embed=bot.embed(
        c=discord.Color.teal(),
        title=f"Attention all {cmd.argstr} subscribers!"))
