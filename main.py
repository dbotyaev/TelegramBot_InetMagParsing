import time
from telegram import Bot
from telegram import ParseMode
from telegram import ReplyKeyboardMarkup
# from telegram import ReplyKeyboardRemove
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Update
# from telegram import ChatAction
from telegram.ext import CallbackContext
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater
from telegram.ext import JobQueue  # Job

import googlesheets
from settings import TG_TOKEN
from validation import *
import parsing
from analytics import TO_BUY, RECEIPT


WELCOME = 'Этот бот предназначен для парсинга товаров и цен интернет-магазинов.\n' \
          'Информация записывается в вашу Google-таблицу и периодически обновляется.\n' \
          'В таблице необходимо установить минимальные цены, и если цена продажи ' \
          'будет ниже или равна минимальной цене, то Вы получите уведомление в телеграм. ' \
          'Значит можно закупать товар по выгодной цене!'
RESTRICTION = 'Внимание! Пока работает парсинг товаров только с wildberries.kz'
MESSAGE_NEW_PARSER = 'Для создания нового парсера введите команду /newparsing'

# кнопки для клавиатуры
CALLBACK_BUTTON_NEW_PARSER = 'Создать новый парсер'
CALLBACK_BUTTON_END_PARSER = 'Отменить'

URL_FOR_PARSER, SPREADSHEET_URL, WORKSHEET_TITLE = range(3)  # точки входа


def get_keyboard():
    # contact_button = KeyboardButton('Отправить контакты', request_contact=True)
    # location_button = KeyboardButton('Отправить геопозицию', request_location=True)
    return ReplyKeyboardMarkup([[CALLBACK_BUTTON_NEW_PARSER, CALLBACK_BUTTON_END_PARSER]],
                               one_time_keyboard=False,  # скрывать клавиатуру
                               resize_keyboard=True)  # оптимизируем размер клавиатуры


def get_inline_keyboard_validation():
    """
    возвращает inline-клавиатуру к сообщению после прохождения опроса по созданию нового парсера
    для проверки, редактирования и сохранения введенных данных
    :return:
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Сохранить и активировать', callback_data='save_parsing'),
            ],
            [
                InlineKeyboardButton(text='Изменить лист в Google-таблице', callback_data='edit_worksheet_title'),
            ],
        ],
    )


def start(update: Update, context: CallbackContext):
    # print(update.message.chat.id)
    # print(update.message.chat_id)
    # добавляет эффект печати ...typing
    # update.message.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    # time.sleep(1)
    update.message.reply_text(f'Привет, {update.message.chat.first_name}!\n'
                              f'{WELCOME}\n'
                              )
    update.message.reply_text(f'{RESTRICTION}')
    update.message.reply_text(MESSAGE_NEW_PARSER, reply_markup=get_keyboard())
    # context.user_data.clear()
    print('start', context.user_data)


def get_text_handler(update: Update, context: CallbackContext):
    print(context.user_data)
    print(update.message.text)
    if update.message.text.lower() in ['отмена', 'отменить', 'cancel'] and context.user_data:
        context.user_data.clear()
        update.message.reply_text('Создание парсера отменено.')
        print('Создание парсера отменено.', context.user_data)
        return
    try:
        if context.user_data['worksheet_title'] == 'edit_worksheet_title':  # условие редактирования листа в таблице
            validation, url = validation_worksheet_title(context.user_data['spreadsheet_url'], update.message.text)
            if validation == 'ok':
                context.user_data['worksheet_title'] = update.message.text
                context.user_data['spreadsheet_url'] = url
                # update.message.reply_text('Проверьте ваши данные еще раз!')
                text = [
                    '<b>Ссылка для парсинга товаров и цен:</b>',
                    context.user_data['url_for_parser'],
                    '<b>Ссылка на Google-таблицу для хранения результатов:</b>',
                    context.user_data['spreadsheet_url'],
                    '<b>Название листа в Google_таблице:</b>',
                    context.user_data['worksheet_title']]
                update.message.reply_text(text='\n'.join(text),
                                          parse_mode=ParseMode.HTML,
                                          reply_markup=get_inline_keyboard_validation(),
                                          disable_web_page_preview=True)
                print(context.user_data)
                return
            elif validation == 'error access':
                update.message.reply_text('Ошибка доступа к Google-таблице. Откройте доступ служебному пользователю '
                                          'с правами "Редактор" и попробуйте еще раз.')
                update.message.reply_text('Служебный пользователь: '
                                          'parser@dbotyaev-wb-parser-gs.iam.gserviceaccount.com')
                update.message.reply_text('Введите название листа в Google-таблице для сохранения данных парсинга.')
                return
            else:
                update.message.reply_text('Возникла ошибка. Попробуйте снова чуть позже. '
                                          'Нажмите кнопку "Создать новый парсер"')
                return
    except KeyError:
        # обрабатываем все неправильные текстовые сообщения вне опроса
        update.message.reply_text('Неправильная команда или сообщение! '
                                  'Попробуйте следующие команды или нажмите кнопки на клавиатуре снизу.\n'
                                  '/start - информация о боте\n'
                                  '/newparsing - создание нового парсера')
        return
    else:
        update.message.reply_text('Неправильная команда или сообщение! Ожидается нажатие одной из кнопок.')
        return


def new_parsing(update: Update, context: CallbackContext):
    # context.user_data.clear()
    if not context.user_data:
        context.user_data['user_id_telegram'] = update.message.from_user.id
        print(type(context.user_data))
        wb_url_button = InlineKeyboardButton(text='Wildberries', url='https://www.wildberries.kz/brandlist/all')
        # marwin_url_button = InlineKeyboardButton(text='Marwin', url='https://www.marwin.kz/brand/')
        inline_keyboard = InlineKeyboardMarkup([[wb_url_button]])
        update.message.reply_text(text='Введите ссылку интернет-магазина со списком товаров для парсинга. '
                                       'Можете нажать на кнопку, чтобы перейти на сайт интернет-магазина и '
                                       'скопировать нужную ссылку.',
                                  reply_markup=inline_keyboard)
        print(context.user_data)
        return URL_FOR_PARSER
    else:
        update.message.reply_text('Команда не доступна в данный момент. Сначала необходимо нажать кнопку "Отменить".')
        return ConversationHandler.END
    # update.message(reply_markup=ReplyKeyboardMarkup([['Cancel']], resize_keyboard=True))


def get_url_for_parser(update: Update, context: CallbackContext):
    if update.message.text.lower() in ['отмена', 'отменить', 'cancel']:
        context.user_data.clear()
        update.message.reply_text('Создание парсера отменено.')
        print('Создание парсера отменено.', context.user_data)
        return ConversationHandler.END
    elif update.message.text.lower() in ['создать новый парсер', '/newparsing']:
        update.message.reply_text('Команда не доступна в данный момент. Сначала необходимо нажать кнопку "Отменить".')
        return URL_FOR_PARSER
    if validation_url_for_parser(update.message.text):
        context.user_data['url_for_parser'] = update.message.text
        update.message.reply_text('Настройте доступ к вашей Google-таблице служебному пользователю '
                                  'с правами "Редактор".'
                                  )
        update.message.reply_text('Служебный пользователь: '
                                  'parser@dbotyaev-wb-parser-gs.iam.gserviceaccount.com')
        gsheet_url_button = InlineKeyboardButton(
            text='Открыть Google-таблицы',
            url='https://docs.google.com/spreadsheets/u/0/?usp=drivesdk')
        inline_keyboard = InlineKeyboardMarkup([[gsheet_url_button]])
        update.message.reply_text('Введите ссылку на Google-таблицу для выгрузки данных парсинга.',
                                  reply_markup=inline_keyboard)
        print(context.user_data)
        return SPREADSHEET_URL
    else:
        update.message.reply_text('Ошибка! Ссылка некорректная или не доступна в данный момент. Попробуйте еще раз.')
        wb_url_button = InlineKeyboardButton(text='Wildberries', url='https://www.wildberries.kz/brandlist/all')
        # marwin_url_button = InlineKeyboardButton(text='Marwin', url='https://www.marwin.kz/brand/')
        inline_keyboard = InlineKeyboardMarkup([[wb_url_button]])
        update.message.reply_text(text='Введите ссылку интернет-магазина со списком товаров для парсинга. '
                                       'Можете нажать на кнопку, чтобы перейти на сайт интернет-магазина и '
                                       'скопировать нужную ссылку.',
                                  reply_markup=inline_keyboard)
        return URL_FOR_PARSER


def get_spreadsheet_url(update: Update, context: CallbackContext):
    if update.message.text.lower() in ['отмена', 'отменить', 'cancel']:
        context.user_data.clear()
        update.message.reply_text('Создание парсера отменено.')
        print('Создание парсера отменено.', context.user_data)
        return ConversationHandler.END
    elif update.message.text.lower() in ['создать новый парсер', '/newparsing']:
        update.message.reply_text('Команда не доступна в данный момент. Сначала необходимо нажать кнопку "Отменить".')
        return SPREADSHEET_URL
    validation, url = validation_spreadsheet_url(update.message.text)  # магия - возвращает словарь двух переменных
    # print('validation', validation)
    # print('url', url)
    if validation == 'ok':
        context.user_data['spreadsheet_url'] = url  # возвращенный url идет без доп.параметров
        update.message.reply_text('Введите название листа в Google-таблице, в который будут сохраняться '
                                  'результаты парсинга. Внимание! Все данные на листе будут удалены. '
                                  'Если листа с таким именем нет, то он создатся автоматически.')
        print(context.user_data)
        return WORKSHEET_TITLE
    elif validation == 'error url':
        update.message.reply_text('Ошибка подключения к Google-таблице! Проверьте ссылку, '
                                  'откройте доступ служебному пользователю с правами "Редактор".')
        update.message.reply_text('Попробуйте снова! Введите ссылку на Google-таблицу')
        return SPREADSHEET_URL
    elif validation == 'error access':
        update.message.reply_text('Ошибка доступа к Google-таблице. Проверьте ссылку, '
                                  'откройте доступ служебному пользователю с правами "Редактор" '
                                  'и попробуйте еще раз.')
        update.message.reply_text('Введите ссылку на Google-таблицу')
        return SPREADSHEET_URL
    elif validation == 'error address':
        update.message.reply_text('Ошибка! Неправильная ссылка на Google-таблицу. Проверьте ссылку, '
                                  'откройте доступ служебному пользователю с правами "Редактор".'
                                  'и попробуйте еще раз.')
        update.message.reply_text('Введите ссылку на Google-таблицу')
        return SPREADSHEET_URL
    else:
        update.message.reply_text('Возникла ошибка. Попробуйте снова чуть позже. '
                                  'Нажмите кнопку "Создать новый парсер"')
        return ConversationHandler.END


def get_worksheet_title(update: Update, context: CallbackContext):
    if update.message.text.lower() in ['отмена', 'отменить', 'cancel']:
        context.user_data.clear()
        update.message.reply_text('Создание парсера отменено.')
        print('Создание парсера отменено.', context.user_data)
        return ConversationHandler.END
    elif update.message.text.lower() in ['создать новый парсер', '/newparsing']:
        update.message.reply_text('Команда не доступна в данный момент. Сначала необходимо нажать кнопку "Отменить".')
        return WORKSHEET_TITLE
    validation, url = validation_worksheet_title(context.user_data['spreadsheet_url'], update.message.text)
    if validation == 'ok':
        context.user_data['worksheet_title'] = update.message.text
        context.user_data['spreadsheet_url'] = url
        # update.message.reply_text('Проверьте ваши данные еще раз!')
        text = [
            '<b>Ссылка для парсинга товаров и цен:</b>',
            context.user_data['url_for_parser'],
            '<b>Ссылка на Google-таблицу для хранения результатов:</b>',
            context.user_data['spreadsheet_url'],
            '<b>Название листа в Google_таблице:</b>',
            context.user_data['worksheet_title']]
        update.message.reply_text(text='\n'.join(text),
                                  parse_mode=ParseMode.HTML,
                                  reply_markup=get_inline_keyboard_validation(),
                                  disable_web_page_preview=True)
        print(context.user_data)
        return ConversationHandler.END
    elif validation == 'error access':
        update.message.reply_text('Ошибка доступа к Google-таблице. Откройте доступ служебному пользователю '
                                  'с правами "Редактор" и попробуйте еще раз.')
        update.message.reply_text('Служебный пользователь: '
                                  'parser@dbotyaev-wb-parser-gs.iam.gserviceaccount.com')
        update.message.reply_text('Введите название листа в Google-таблице для сохранения данных парсинга.')
        return WORKSHEET_TITLE
    else:
        update.message.reply_text('Возникла ошибка. Попробуйте снова чуть позже. '
                                  'Нажмите кнопку "Создать новый парсер"')
        return ConversationHandler.END

    # update.message.reply_text(text='Проверяем данные ...',
    #                           reply_markup=ReplyKeyboardRemove())
    # добавляет эффект печати ...typing
    # update.message.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
    # time.sleep(1)


def cancel_handler(update: Update, context: CallbackContext):
    return ConversationHandler.END


def callback_inline_buttons(update: Update, context: CallbackContext):
    print(update.callback_query)
    print(update.effective_message)
    data = update.callback_query.data
    try:
        if context.user_data['url_for_parser'] \
                and context.user_data['spreadsheet_url'] \
                and context.user_data['worksheet_title']:
            if data == 'save_parsing':
                context.user_data['status'] = 'Активен'
                reply_text = googlesheets.add_new_parsing(list(context.user_data.values()))
                if reply_text:
                    update.callback_query.answer(text='Данные успешно сохранены и парсинг активирован.',
                                                 show_alert=True)
                    context.user_data.clear()
                    update.callback_query.edit_message_text(
                        text=update.effective_message.text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True)
                    update.callback_query.message.reply_text(MESSAGE_NEW_PARSER, reply_markup=get_keyboard())
                else:
                    update.callback_query.answer(text='Возникла ошибка, попробуйте еще раз.',
                                                 show_alert=True)
            elif data == 'edit_worksheet_title':
                context.user_data['worksheet_title'] = 'edit_worksheet_title'
                update.callback_query.message.delete()
                update.callback_query.message.reply_text(
                    'Введите название листа в Google-таблице, в который будут сохраняться '
                    'результаты парсинга. Внимание! Все данные на листе будут удалены. '
                    'Если листа с таким именем нет, то он создатся автоматически.')
    except KeyError:
        update.callback_query.edit_message_text(
            text=update.effective_message.text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
        update.callback_query.answer(text='Данные устарели. Операция невозможна.', show_alert=True)
    print(context.user_data)


def get_parsing_job(context: CallbackContext):
    print('Запущен плановый парсинг')
    results_parsing = parsing.parsing_from_settings()  # получаем список результата парсинга со статусами товаров
    for key in results_parsing.keys():
        # print(key)
        for values in results_parsing[key]:
            # print(values)
            if TO_BUY in values[-1] or RECEIPT in values[-1]:
                # print(values[-1])
                text = [
                    '<b>УВЕДОМЛЕНИЕ! Появились товары со статусом "К покупке" или "Поступление".</b>',
                    'Ссылка на интернет-магазин:',
                    values[0],
                    'Название листа в Google_таблице:',
                    '<b>{}</b>'.format(values[2])]
                gsheet_url_button = InlineKeyboardButton(
                    text='Открыть Google-таблицу',
                    url=values[1])
                inline_keyboard = InlineKeyboardMarkup([[gsheet_url_button]])
                context.bot.send_message(
                    chat_id=key,
                    text='\n'.join(text),
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_keyboard)
                print('Отправлены сообщения об изменении статуса товаров пользователю', key)
    print('Плановый парсинг завершен')


def main():
    # создание бота
    bot = Bot(token=TG_TOKEN)
    print(bot.get_me())

    # создание обработчиков событий от бота
    updater = Updater(bot=bot, use_context=True)

    command_start = CommandHandler('start', start)

    newparser_handler = ConversationHandler(
        entry_points=[
            CommandHandler('newparsing', new_parsing, pass_user_data=True),
            MessageHandler(Filters.regex('Создать новый парсер'), new_parsing, pass_user_data=True)
        ],
        states={
            URL_FOR_PARSER: [
                MessageHandler(Filters.text, get_url_for_parser, pass_user_data=True),
            ],
            SPREADSHEET_URL: [
                MessageHandler(Filters.text, get_spreadsheet_url, pass_user_data=True),
            ],
            WORKSHEET_TITLE: [
                MessageHandler(Filters.text, get_worksheet_title, pass_user_data=True),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_handler),
        ],
    )

    inline_buttons = CallbackQueryHandler(callback=callback_inline_buttons, pass_chat_data=True)

    text_handler = MessageHandler(Filters.text, get_text_handler, pass_user_data=True)

    updater.dispatcher.add_handler(command_start)
    updater.dispatcher.add_handler(newparser_handler)
    updater.dispatcher.add_handler(inline_buttons)
    updater.dispatcher.add_handler(text_handler)

    parsing_job = JobQueue()
    parsing_job.set_dispatcher(updater.dispatcher)
    parsing_job.run_repeating(callback=get_parsing_job, interval=7200)

    # запуск бота и бесконечная обработка событий
    updater.start_polling(clean=True)

    parsing_job.start()
    # parsing_job.tick()

    updater.idle()


if __name__ == '__main__':
    main()
