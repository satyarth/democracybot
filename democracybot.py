from telegram.ext import Updater, CommandHandler, Job
from recordclass import recordclass
from textwrap import dedent
from config import key


Session = recordclass('Session', ['exiler', 'exilee_id', 'votes'])
Settings = recordclass('Settings', ['quorum', 'timer'])


def update_votes(bot, chat_id):
    s = sessions[chat_id]
    print(s.votes)
    response = "✅ votes:" + str(len([None for voter in s.votes if s.votes[voter]])) + "\n"
    response += "✖ votes:" + str(len([None for voter in s.votes if not s.votes[voter]]))
    bot.sendMessage(chat_id, text=response)


def init_settings(bot, chat_id):
    member_count = bot.getChatMembersCount(chat_id)
    quorum = int(member_count*0.4)
    settings[chat_id] = Settings(quorum, 60)
    bot.sendMessage(chat_id, text="Bot settings initialized.\n" +
                                  "Quorum: " + str(quorum) + "\n"+
                                  "Timer: 60s")

def start(bot, update):
    chat_id = update.message.chat_id
    if chat_id not in sessions:
        init_settings(bot, update.message.chat_id)
        bot.sendMessage(update.message.chat_id, 
            text=dedent('''\
                        Hi! Prepare to be fucked by the long dick of the law.
                        How it works:
                        * Nominate someone for kicking by replying to their comment with /ban
                        * Voting begins
                        * In order for voting to be valid, a minimum number of participants (quorum) must be reached.
                        * Once the quorum is reached, majority wins.'''))
    else:
        bot.sendMessage(chat_id, "Error: One #beef at a time, ladies 🐄🐮🐃🍴")
        return

#TODO
def update_settings(bot, update):
    chat_id = update.message.chat_id
    if chat_id in sessions:
        bot.sendMessage(chat_id, "Please resolve ongoing motion first.")
        return
    if chat_id not in settings:
        init_settings(bot, chat_id)
    pass


def ban(bot, update, job_queue):
    try:
        exilee_id = update.message.reply_to_message.from_user.id
        exilee_username = update.message.reply_to_message.from_user.username
    except AttributeError:
        bot.sendMessage(chat_id, "Usage: reply to a comment of the person you want to kick with /ban")
    exiler = update.message.from_user['username']
    chat_id = update.message.chat_id
    if chat_id in sessions:
        bot.sendMessage(chat_id, "Error: One #beef at a time, ladies 🐄🐮🐃🍴")
        return
    if chat_id not in settings:
        init_settings(bot, chat_id)

    s = Session(exiler, exilee_id, dict())
    print("Initiating", s, exilee_username)
    bot.sendMessage(chat_id, text=exilee_username+ " nominated for banning by " + s.exiler + \
        "\nVote with /yes or /no\nTimer: " + str(settings[chat_id].timer) + "s\nQuorum: " + str(settins[chat_id].quorum))

    job = Job(conclude, settings[chat_id].timer, repeat=False, context=chat_id)
    job_queue.put(job)
    jobs[chat_id] = job
    sessions[chat_id] = s


def active_session(func):
    def inner(bot, update, *args):
        chat_id = update.message.chat_id
        if chat_id in sessions:
            return func(bot, update, *args)
        else:
            bot.sendMessage(update.message.chat_id, text="Not in a session. Start some shit with /ban first.")
    return inner


@active_session
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


@active_session    
def abort(bot, update):
    chat_id = update.message.chat_id
    s = sessions[chat_id]
    if update.message.from_user['username'] == s.exiler:
        bot.sendMessage(chat_id, text="Banning aborted by " + s.exiler)
        job = jobs[chat_id]
        job.schedule_removal()
        del jobs[chat_id]
        del sessions[chat_id]
    else:
        bot.sendMessage(chat_id, text="Banning can only be aborted by " + s.exiler)


def conclude(bot, job):
    chat_id = job.context
    s = sessions[chat_id]
    set_ = settings[chat_id]
    if len(s.votes) >= set_.quorum and len([None for voter in s.votes if s.votes[voter]]) > len([None for voter in s.votes if not s.votes[voter]]):
        bot.sendMessage(chat_id, text='Voting over. Motion passed.')
        bot.kickChatMember(chat_id, s.exilee_id)
    else:
        bot.sendMessage(chat_id, text='Voting over. Failed.')
        if len(s.votes) >= set_.quorum:
            bot.sendMessage(chat_id, text='Quorum not reached.')

    del sessions[chat_id]



def main():
    updater = Updater(key)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ban", ban, pass_job_queue=True))
    dp.add_handler(CommandHandler("abort", abort))
    dp.add_handler(CommandHandler("yes", yes))
    dp.add_handler(CommandHandler("no", no))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    sessions = dict()
    settings = dict()
    jobs = dict()
    main()