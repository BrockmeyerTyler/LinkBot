
import random
import re

from linkbot.utils.misc import send_split_message
from linkbot.utils.cmd_utils import *


@command(
    ["{c} <#id>", "{c} list [author]", "{c} random [author]",
     "{c} add <quote -author>", "{c} remove <#id>"],
    "Get a quote, list them all or add/remove a quote.",
    [
        ("{c} 21", "Writes the quote with an ID of 21. If you don't know the quote ID, use:"),
        ("{c} list", "Lists all quote for the server."),
        ("{c} list LocalIdiot", "This will show all quotes from LocalIdiot."),
        ("{c} random", "Gets a random quote from the server."),
        ("{c} random Jimbob", "gets a random quote from Jimbob."),
        ("{c} add Hey, it's me! -Dawson", "This will add \"Hey, it's me\" as a quote from Dawson."),
        ("{c} add Anyone: Hey Daws.\nDawson: Seeya!",
         "You can separate different parts of a quote using a new line (shift+enter)."),
        ("{c} remove 12",
         "This will remove the quote that has an ID of 12. Remember to check 'quote list' to get the ID!")
    ]
)
@restrict(SERVER_ONLY)
@require_args(1)
async def quote(cmd: Command):
    subcmd = cmd.args[0]
    cmd.shiftargs()
    if subcmd.isdigit():
        await quote_id(cmd, int(subcmd))
    elif subcmd.lower() == "random":
        await quote_random(cmd)
    elif subcmd.lower() == "list":
        await quote_list(cmd)
    elif subcmd.lower() == "add":
        await quote_add(cmd)
    elif subcmd.lower() == "remove":
        await quote_remove(cmd)
    else:
        raise CommandSyntaxError(cmd, 'Invalid sub-command.')


async def quote_id(cmd, qid):
    # check that quote id is within bounds
    with db.connect() as (conn, cur):
        cur.execute("SELECT author, quote FROM quotes WHERE server_id = %s AND id = %s;", [cmd.guild.id, qid])
        result = cur.fetchone()
    if not result:
        raise CommandSyntaxError(cmd, f'`{qid}` is not a valid quote ID.')
    author, text = result[0]
    await cmd.channel.send(f'{_nlrepl(text)}\n\t\t\t-{author}')


async def quote_list(cmd):
    with db.connect() as (conn, cur):
        if cmd.args:
            author = cmd.args[0]
            cur.execute("SELECT id, quote FROM quotes WHERE server_id = %s AND author = %s;",
                        [cmd.guild.id, author])
            result = cur.fetchall()
            if not result:
                raise CommandError(cmd, f"I don't know any quotes from {author}.")
            result = sorted(result, key=lambda x: x[0])
            await send_split_message(cmd.channel, f"Quotes from {author}:\n  " + "\n  ".join(
                [f"`{q_id}:` {text}" for (q_id, text) in result]))
        else:
            cur.execute("SELECT id, author, quote FROM quotes WHERE server_id = %s;",
                        [cmd.guild.id])
            result = cur.fetchall()
            if not result:
                raise CommandError(cmd, "I don't know any quotes from this server.")
            result = sorted(result, key=lambda x: x[0])
            await send_split_message(cmd.channel, "\n".join(
                [f"**{q_id}:** {_nlrepl(text)}    -{author}" for (q_id, author, text) in result]))


async def quote_random(cmd):
    random.seed()
    with db.connect() as (conn, cur):
        if cmd.args:
            author = cmd.args[0]
            cur.execute("SELECT id, quote FROM quotes WHERE server_id = %s AND author = %s;",
                        [cmd.guild.id, author])
            result = cur.fetchall()
            if not result:
                raise CommandError(cmd, f"I don't know any quotes from {author}.")
            (q_id, text) = random.choice(result)
            await cmd.channel.send(f"`  {q_id}:` {_nlrepl(text)}    -{author}")
        else:
            cur.execute("SELECT id, author, quote FROM quotes WHERE server_id = %s;",
                        [cmd.guild.id])
            result = cur.fetchall()
            if not result:
                raise CommandError(cmd, "I don't know any quotes from this server.")
            (q_id, author, text) = random.choice(result)
            await cmd.channel.send(f"`  {q_id}:` {_nlrepl(text)}    -{author}")


@restrict(ADMIN_ONLY)
@require_args(2)
async def quote_add(cmd):
    q_args = cmd.argstr
    match = re.search('( -\w)', q_args)

    # Author of Quote check
    if match is None:
        raise CommandSyntaxError(cmd, 'To add a quote, include a quote followed by -Author\'s Name.')
    author, text = (q_args[match.start() + 2:], q_args[:match.start()].replace('\n', '\\n'))

    with db.connect() as (conn, cur):
        cur.execute("SELECT id FROM quotes WHERE server_id = %s;", [cmd.guild.id])
        result = [r[0] for r in cur.fetchall()]
        for (i, j) in enumerate(result):
            if i != j:
                q_id = i
                break
        else:
            q_id = len(result)
        cur.execute(f"INSERT INTO quotes (server_id, id, author, quote) VALUES (%s, %s, %s, %s);",
                    [cmd.guild.id, q_id, author, text])
        conn.commit()
    await cmd.channel.send(
        f"Added quote with ID {q_id}: \n{_nlrepl(text)} -{author}")


@restrict(ADMIN_ONLY)
@require_args(1)
async def quote_remove(cmd):
    # ID type-check
    try:
        q_id = int(cmd.args[0])
    except TypeError:
        raise CommandSyntaxError(cmd, str(cmd.args[0]) + ' is not a valid quote ID.')
    except IndexError:
        raise CommandSyntaxError(cmd, "You must provide a quote ID to remove.")

    with db.connect() as (conn, cur):
        cur.execute("SELECT author, quote FROM quotes WHERE server_id = %s AND id = %s;", [cmd.guild.id, q_id])
        result = cur.fetchone()
        if not result:
            raise CommandError(cmd, f"There is not a quote for this server with an id of {q_id}.")
        (author, text) = result
        cur.execute("DELETE FROM quotes WHERE server_id = %s AND id = %s;", [cmd.guild.id, q_id])
        conn.commit()
    await cmd.channel.send(f"Quote removed: ~~{_nlrepl(text)}~~\n\t\t\t-~~{author}~~")


def _nlrepl(q):
    return q.replace('\\n', '\n')