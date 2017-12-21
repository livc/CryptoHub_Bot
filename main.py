from pymongo import MongoClient
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Updater, CommandHandler, Filters, RegexHandler, ConversationHandler

from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import InlineQueryHandler
import logging
import json
import os.path


client = MongoClient()

db = client.test.tggroup

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = './config.json'
CONFIG_USER = './config_user.json'

if os.path.isfile(CONFIG_USER):
    CONFIG = CONFIG_USER

DESC, LINK, INPUTLINK, CONFIRM, INSERT, TAG, SHOW, LIST = range(8)
config = json.load(open(CONFIG, encoding='utf-8'))


def facts_to_str(user_data):
    facts = list()
    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))
    return "\n".join(facts).join(['\n', '\n'])


def group_info(dict):
    rtn = {}
    for key, value in dict.items():
        if key == 'title':
            rtn['群组名称 Name'] = dict['title']
        if key == 'categ':
            rtn['类别 Category'] = dict['categ']
        if key == 'link':
            rtn['群组链接 Link'] = dict['link']
        if key == 'tag' and value != '':
            rtn['货币名称 Coin Name'] = dict['tag']
        if key == 'desc':
            rtn['群组描述 Description'] = dict['desc']
    return rtn


def print_html(dict):
    text = ''
    for i in db.find(dict).sort([('tag', 1)]):
        text += '<a href="' + i['link'] + '">' + i['title'] + '</a> \n'
    return text


def kb(list):
    k = []
    tmp = []
    for i in list:
        tmp.append(i)
        if len(tmp) == 2 or i == list[-1]:
            k.append(tmp)
            tmp = []
    return k


def join(bot, update, user_data):
    # ‘private’, ‘group’, ‘supergroup’ or ‘channel’.
    # chat with bot can't use command join
    if update.effective_chat.type == 'private':
        return
    # only admin can use command join in chat
    crt = ['creator', 'administrator']
    admin = [i.user.id for i in bot.get_chat_administrators(update.message.chat.id) if i.status in crt]
    if update.message.from_user.id not in admin:
        # update.message.reply_text('只有管理员能操作')
        return
    url = 'https://t.me/Crypt0Hub_Bot?start=' + str(update.message.chat_id)
    user_data['official'] = 0
    user_data['title'] = update.effective_chat.title
    user_data['admin_id'] = update.message.from_user.id
    user_data['group_id'] = update.message.chat_id
    if update.effective_chat.username is None:
        user_data['public'] = 0
    else:
        user_data['public'] = 1
        user_data['link'] = 'https://t.me/' + update.effective_chat.username
    keyboard = [[InlineKeyboardButton("下一步 Next", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('继续 Continue', reply_markup=reply_markup, one_time_keyboard=True)


def start(bot, update, args, user_data):
    if len(args) == 0:
        bot.send_message(chat_id=update.message.chat_id, text='233')
    else:
        k = kb(config['categories'])
        update.message.reply_text('请选择群组所属分类 \nSelect the category of your group pls.',
                                  reply_markup=ReplyKeyboardMarkup(k, one_time_keyboard=True))
        return DESC


def desc(bot, update, user_data):
    user_data['tag'] = ''
    user_data['categ'] = update.message.text
    if user_data['categ'] == '数字货币Cryptocurrency':
        update.message.reply_text('请输入货币名称(英文缩写) \nType the coin name(abbreviation) pls.')
        return TAG
    else:
        update.message.reply_text('请输入群组描述 \nType the description of your group pls.')
        return LINK


def tag(bot, update, user_data):
    user_data['tag'] = update.message.text.upper()
    update.message.reply_text('请输入群组描述 \nType the description of your group pls.')
    return LINK


def getlink(bot, update, user_data):
    user_data['desc'] = update.message.text
    if user_data['public'] == 0:
        update.message.reply_text('请输入群组链接 \nType your group invitation link pls.')
    else:
        update.message.reply_text('群组链接为:'+user_data['link']+'\n'+'Link: '+user_data['link'],
                                  reply_markup=ReplyKeyboardMarkup([['继续 Next']],
                                  one_time_keyboard=True))
    return CONFIRM


def confirm(bot, update, user_data):
    if user_data['public'] == 0:
        user_data['link'] = update.message.text
    else:
        pass
    update.message.reply_text(
            '请确认群组信息 \nConfirm info pls.''{}'.format(facts_to_str(group_info(user_data))),
            reply_markup=ReplyKeyboardMarkup([['Yes', 'No']], one_time_keyboard=True))
    return INSERT


def insert(bot, update, user_data):
    if update.message.text == 'Yes':
        cnt = db.find({'group_id': user_data['group_id']}).count()
        if cnt > 0:
            update.message.reply_text('群组已存在 \nAlready exists', reply_markup=ReplyKeyboardRemove())
        else:
            db.insert_one(user_data)
            update.message.reply_text('收录成功！\nSuccess!', reply_markup=ReplyKeyboardRemove())
            bot.send_message(chat_id=config['channel'], text=format(facts_to_str(group_info(user_data))))
    else:
        update.message.reply_text('已取消 Cancel', reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def check(bot, update, args):
    if len(args) == 0:
        update.message.reply_text('eg: `/check BTC`')
        return
    coin = args[0].upper()
    text = ''
    for i in db.find({'tag': coin}):
        text += '<a href="' + i['link'] + '">' + i['title'] + '</a> \n'
    bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode='HTML')


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")
    bot.send_message(chat_id=update.message.chat_id, text=update.message.chat_id)


def cancel(bot, update, user_data=None):
    if user_data is not None:
        user_data.clear()
    update.message.reply_text('cancel', reply_markup=ReplyKeyboardRemove())


def delete(bot, update, user_data):
    userid = update.message.from_user.id
    user_data['admin_id'] = userid
    rtn = [i['title'] for i in db.find({'admin_id': userid})]
    print(rtn)
    update.message.reply_text('请选择要删除的群组 \nSelect the group you want to remove pls.',
                              reply_markup=ReplyKeyboardMarkup(kb(rtn), one_time_keyboard=True))
    return SHOW


def show(bot, update, user_data):
    title = update.message.text
    db.remove({'admin_id': user_data['admin_id'], 'title': title})
    update.message.reply_text('删除成功 \nRemoval success.', reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def list_categ(bot, update):
    k = kb(config['categories'])
    update.message.reply_text('请选择群组分类 \nSelect the category you wanna search pls.',
                              reply_markup=ReplyKeyboardMarkup(k))
    return LIST


def select_categ(bot, update):
    categ = update.message.text
    text = print_html({'categ': categ})
    bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode='HTML')
    return LIST


def inline_caps(bot, update):
    query = update.inline_query.query
    if not query:
        return
    query = query.upper()
    results = list()
    coins = db.distinct('tag')
    for coin in coins:
        if query in coin:
            results.append(
                InlineQueryResultArticle(
                    id=coin,
                    title=coin,
                    input_message_content=InputTextMessageContent(print_html({'tag': coin}), parse_mode=ParseMode.HTML),
                    )
                )

    bot.answer_inline_query(update.inline_query.id, results)


def main():
    updater = Updater(token=config['bot'])
    dp = updater.dispatcher

    group_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, pass_args=True, pass_user_data=True)],

        states={
            DESC: [RegexHandler('^(' + '|'.join((config['categories'])) + ')$', desc, pass_user_data=True)],
            CONFIRM: [MessageHandler(Filters.text, confirm, pass_user_data=True)],
            INSERT: [RegexHandler('^(Yes|No)$', insert, pass_user_data=True)],
            LINK: [MessageHandler(Filters.text, getlink, pass_user_data=True)],
            TAG: [RegexHandler('^[A-Za-z]+$', tag, pass_user_data=True)]
        },

        fallbacks=[CommandHandler('cancel', cancel, pass_user_data=True)]
    )

    delete_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', delete, pass_user_data=True)],

        states={
            SHOW: [MessageHandler(Filters.text, show, pass_user_data=True)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    list_handler = ConversationHandler(
        entry_points=[CommandHandler('list', list_categ)],

        states={
            LIST: [MessageHandler(Filters.text, select_categ)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    join_handler = CommandHandler('join', join, pass_user_data=True)
    check_handler = CommandHandler('check', check, pass_args=True)

    inline_caps_handler = InlineQueryHandler(inline_caps)
    dp.add_handler(inline_caps_handler)

    dp.add_handler(list_handler)
    dp.add_handler(check_handler)
    dp.add_handler(join_handler)
    dp.add_handler(group_handler)
    dp.add_handler(delete_handler)
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
