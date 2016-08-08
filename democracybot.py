from telegram.ext import Updater, CommandHandler, Job
import logging
from recordclass import recordclass
from textwrap import dedent
from math import ceil
from config import key

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

Session = recordclass('Session', ['initiator', 'action', 'votes'])
Settings = recordclass('Settings', ['quorum', 'timer'])



def session_closed(func):
    def inner(bot, update, *args, **kwargs):
        chat_id = update.message.chat_id
        if chat_id in sessions:
            bot.sendMessage(chat_id, text="Error: One #beef at a time, ladies 🐄🐮🐃🍴")
            return
        return func(bot, update, *args, **kwargs)
    return inner


def session_open(func):
    def inner(bot, update, *args, **kwargs):
        chat_id = update.message.chat_id
        if chat_id not in sessions:
            bot.sendMessage(chat_id, text="Not in a session. Start some shit with /kick first.")
            return
        return func(bot, update, *args, **kwargs)
    return inner


def is_reply(func):
    def inner(bot, update, *args, **kwargs):
        if not update.message.reply_to_message:
            bot.sendMessage(update.message.chat_id, "Usage: reply to a message of the person you want to act on")
            return
        return func(bot, update, *args, **kwargs)
    return inner


def update_votes(bot, chat_id):
    s = sessions[chat_id]
    print(s.votes)
    response = "✅ votes:" + str(len([None for voter in s.votes if s.votes[voter]])) + "\n"
    response += "✖ votes:" + str(len([None for voter in s.votes if not s.votes[voter]]))
    bot.sendMessage(chat_id, text=response)


def init_settings(bot, chat_id):
    member_count = bot.getChatMembersCount(chat_id)
    quorum = max(3, ceil(member_count*0.3))
    settings[chat_id] = Settings(quorum, 60)
    bot.sendMessage(chat_id, text="Bot settings initialized.\n" +
                                  "Quorum: " + str(quorum) + "\n"+
                                  "Timer: 60s")
@session_closed
def start(bot, update):
    chat_id = update.message.chat_id
    init_settings(bot, update.message.chat_id)
    bot.sendMessage(update.message.chat_id, 
        text=dedent('''\
                    Hi! Prepare to be fucked by the long dick of the law.
                    How it works:
                    * Nominate someone for kicking by replying to their message with /kick
                    * Voting begins
                    * In order for voting to be valid, a minimum number of participants (quorum) must be reached.
                    * Once the quorum is reached, majority wins.'''))

#TODO
def update_settings(bot, update):
    chat_id = update.message.chat_id
    if chat_id in sessions:
        bot.sendMessage(chat_id, "Please resolve ongoing motion first.")
        return
    if chat_id not in settings:
        init_settings(bot, chat_id)
    pass

@session_closed
@is_reply
def kick(bot, update, job_queue):
    chat_id = update.message.chat_id
    exilee_id = update.message.reply_to_message.from_user.id
    exilee_username = update.message.reply_to_message.from_user.username
    exiler_id = update.message.from_user['id']
    exiler_username = update.message.from_user['username']

    if chat_id not in settings:
        init_settings(bot, chat_id)

    bot.sendMessage(chat_id, text=exilee_username+ " nominated for kicking by " + exiler_username + \
        "\nVote with /yes or /no\nTimer: " + str(settings[chat_id].timer) + "s\nQuorum: " + str(settings[chat_id].quorum))

    job = Job(conclude, settings[chat_id].timer, repeat=False, context=chat_id)
    job_queue.put(job)
    jobs[chat_id] = job
    sessions[chat_id] = Session(exiler_id, lambda:bot.kickChatMember(chat_id, exilee_id), dict())


@session_open
def cast(bot, update, vote):
    chat_id = update.message.chat_id
    s = sessions[chat_id]
    if update.message.from_user['username'] not in s.votes:
        s.votes[update.message.from_user['username']] = vote
        bot.sendMessage(chat_id, text="Vote registered 👍")
        update_votes(bot, chat_id)
    else:
        bot.sendMessage(chat_id, text="👀 voter fraud tbh fam 👀")


def yes(bot, update):
    cast(bot, update, True)


def no(bot, update):
    cast(bot, update, False)


@session_open
def abort(bot, update):
    chat_id = update.message.chat_id
    s = sessions[chat_id]
    if update.message.from_user['id'] == s.initiator:
        bot.sendMessage(chat_id, text="Kicking aborted")
        job = jobs[chat_id]
        job.schedule_removal()
        del jobs[chat_id]
        del sessions[chat_id]
    else:
        bot.sendMessage(chat_id, text="Kicking can only be aborted by the initiator")


def conclude(bot, job):
    chat_id = job.context
    s = sessions[chat_id]
    set_ = settings[chat_id]
    response = "Voting over\n"
    if len(s.votes) >= set_.quorum and len([None for voter in s.votes if s.votes[voter]]) > len([None for voter in s.votes if not s.votes[voter]]):
        response += 'Motion passed\n'
        s.action()
    else:
        response += 'Motion failed\n'
        if len(s.votes) <= set_.quorum:
            response += 'Quorum not reached'
    bot.sendMessage(chat_id, text=response)
    del sessions[chat_id]


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(key)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("kick", kick, pass_job_queue=True))
    dp.add_handler(CommandHandler("abort", abort))
    dp.add_handler(CommandHandler("yes", yes))
    dp.add_handler(CommandHandler("no", no))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    sessions = dict()
    settings = dict()
    jobs = dict()
    main()