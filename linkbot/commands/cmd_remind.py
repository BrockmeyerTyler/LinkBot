
import re
from datetime import datetime, timedelta

import linkbot.utils.queries.reminder as queries
from linkbot.utils.cmd_utils import *

_delay_regex = re.compile(r"(?:(?:(\d+)d ?)|(?:(\d+)h ?)|(?:(\d+)m ?)|(?:(\d+)s ?))+")
REMINDER_LOOP_TIME = 900


@command(
    ['{c} me [about <reason>] in #d#h#m#s', '{c} purge'],
    "Mentions you in a message once the given amount of time has passed.",
    [
        ('{c} in 1d 10m', 'Reminds you via a direct message in 1 days and 10 minutes.'),
        ('{c} me of bedtime in 1h 3s', 'Sends you a reminder in 1 hour and 3 seconds.'),
        ('{c} purge', 'Removes all reminders that are set for you.')
    ]
)
@require_args(1)
async def remind(cmd: Command):
    if cmd.args[0] == 'purge':
        with db.Session.new() as sess:
            await queries.delete_reminders_for_user(sess, cmd.author.id)
        await send_success(cmd.message)
        return

    # Parse the optional args and qol words.
    try:
        reason = ''
        if cmd.args[0].lower() == 'me':
            cmd.shiftargs()
        if cmd.args[0].lower() == 'of' or cmd.args[0].lower() == 'about':
            cmd.shiftargs()
            while True:
                if not cmd.args:
                    raise CommandSyntaxError(cmd, 'Tell me when to remind you with `in #d#h#m#s`.')
                elif cmd.args[0] == 'in' and _delay_regex.match(cmd.argstr[3:].strip()):
                    break
                reason += cmd.args[0] + ' '
                cmd.shiftargs()
            reason = reason[:-1]
        if cmd.args[0] == 'in':
            cmd.shiftargs()
    except IndexError:
        raise CommandSyntaxError(cmd, 'You need to specify a delay.')

    # Parse the delay.
    try:
        match = _delay_regex.match(cmd.argstr)
        if match:
            days = match.group(1) or 0
            hours = match.group(2) or 0
            minutes = match.group(3) or 0
            seconds = match.group(4) or 0
            delay = int(seconds) + 60 * int(minutes) + 3600 * int(hours) + 86400 * int(days)
        else:
            raise CommandSyntaxError(cmd, 'Delay specification is not in a valid format.')
    except ValueError:
        raise CommandSyntaxError(cmd, 'Days, hours, minutes and seconds can only be whole numbers.')

    now = datetime.now()
    remind_at = now + timedelta(seconds=delay)

    if delay < REMINDER_LOOP_TIME:
        client.loop.create_task(remind_soon(cmd.author, remind_at, reason))
    else:
        async with await db.Session.new() as sess:
            await queries.create_reminder(sess, cmd.author.id, remind_at, reason)

    # Exclude date from notification if the reminder will occur within 24 hours.
    if delay < 85000:
        outstring = remind_at.strftime("I'll remind you at %r")
    else:
        outstring = remind_at.strftime("I'll remind you on %a, %b %e at %r")

    # Include reason in the notification if it was provided.
    if reason != '':
        outstring += f' about "{reason}".'
    else:
        outstring += '.'
    await cmd.channel.send(embed=bot.embed(
        c=discord.Color.blue(),
        title="Reminder",
        description=outstring))


@background_task
async def remind_loop():
    delta_time = timedelta(seconds=REMINDER_LOOP_TIME + 1)
    while not client.is_closed():
        min_time = datetime.now() + delta_time
        async with await db.Session.new() as sess:
            reminders = await queries.get_reminders_before(sess, min_time)
            if reminders:
                ids = [r[0] for r in reminders]
                await queries.delete_reminders_with_ids(sess, ids)
        for (_, remindee_id, remind_at, reason) in reminders:
            remindee = client.get_user(remindee_id)
            client.loop.create_task(remind_soon(remindee, remind_at, reason))
        await asyncio.sleep(REMINDER_LOOP_TIME)


async def remind_soon(remindee, remind_at, reason):
    delta_time = (remind_at - datetime.now()).total_seconds()
    await asyncio.sleep(delta_time)
    if reason == '':
        await remindee.send(embed=bot.embed(
            c=discord.Color.blue(),
            title="Reminder",
            description=f'{emoji.Symbol.calendar} This is your reminder {remindee.name}!'))
    else:
        await remindee.send(embed=bot.embed(
            c=discord.Color.blue(),
            title="Reminder",
            description=f'{emoji.Symbol.calendar} I\'m reminding you about "{reason}", {remindee.name}!'))
