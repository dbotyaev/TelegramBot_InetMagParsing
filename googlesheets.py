import os
# import pandas as pd
import pygsheets
# import pandas as pd
from settings import SERVICE_ACCOUNT_FILE, \
    URL_GOOGLESHEET_SETTINGS, \
    NAME_WORKSHEET_SETTINGS, \
    NAME_RANGE_SETTINGS
from batchupdate_to_googlesheets import requests_to_googlesheet

# для обработки ошибок
from google.auth import exceptions as google_exceptions
from googleapiclient.errors import HttpError as google_HttpError


HEADERS = [
    'ID товара',
    'Наименование товара',
    'Брэнд',
    'Текущая цена',
    'Старая цена',
    'Ссылка на товар',
    'ID похожих товаров',
    'Дата',
    'Статус',
    'Минимальная цена'
]

HEADERS_FROM_FILE = (
    'id_product',
    'f_product',
    'f_brand',
    'f_price',
    'f_price_old',
    'f_url_product',
    'f_similar_id',
    'f_data_parsing',
    'f_status_product',
    'f_min_price'
)


def connection_api_gsheet():
    path = os.path.join(os.getcwd(), SERVICE_ACCOUNT_FILE)
    client = pygsheets.authorize(service_account_file=path)

    # Примеры
    # очищаем базовый фильтр на листе
    # client.sheet.batch_update(spreadsheet_id='1Sx9INT-i8vexP6n2EtD524mybDG3tsppYqusinJHlTE',
    #                                 requests={'clearBasicFilter': {'sheetId': 0}})
    # создаем базовый фильтр
    # client.sheet.batch_update(spreadsheet_id='1Sx9INT-i8vexP6n2EtD524mybDG3tsppYqusinJHlTE',
    #                                      requests={'setBasicFilter': {'filter': {}}})
    # Закрепление строки
    # client.sheet.batch_update(spreadsheet_id='1Sx9INT-i8vexP6n2EtD524mybDG3tsppYqusinJHlTE',
    #                           requests={
    #                               "updateSheetProperties":
    #                                   {"properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
    #                                    "fields": "gridProperties.frozenRowCount"}}
    #                           )
    return client


def load_settings_for_parsing():
    # path = os.path.join(os.getcwd(), SERVICE_ACCOUNT_FILE)
    # client = pygsheets.authorize(service_account_file=path)
    client = connection_api_gsheet()
    try:
        google_sheet = client.open_by_url(URL_GOOGLESHEET_SETTINGS)
        worksheet = google_sheet.worksheet_by_title(NAME_WORKSHEET_SETTINGS)
        c_range = worksheet.get_named_range(NAME_RANGE_SETTINGS).range
        return worksheet.range(c_range, returnas='matrix')[1:]
    except google_exceptions.TransportError:
        print('Нет подключения к Google-таблице')
        return []
    except google_HttpError:
        print('Нет доступа к Google-таблице')
        return []
    except pygsheets.exceptions.WorksheetNotFound:
        print('Такого листа не существует')
        return []
    except pygsheets.exceptions.RangeNotFound:
        print('Такого именнованного диапазоне не существует')
        return []
    except Exception:
        print('Что-то пошло не так')
        return []


def load_file_parsing_from_gsheet(spreadsheet_url, worksheet_title):
    client = connection_api_gsheet()
    # print('client', client.open_as_json('1isnF-mmqRPjifJTvLSGRKbbLInrsCZbTWZ-WLNN7Ruo'))
    google_sheet = client.open_by_url(spreadsheet_url)
    # print('google_sheet', google_sheet.to_json())
    # print(google_sheet.to_json())

    # если при чтении листа не существует, создаем его
    try:
        worksheet = google_sheet.worksheet_by_title(worksheet_title)
    except pygsheets.exceptions.WorksheetNotFound:
        google_sheet.add_worksheet(worksheet_title)
        worksheet = google_sheet.worksheet_by_title(worksheet_title)

    try:
        # df_from_file = worksheet.get_named_range(worksheet_title)
        # start_addr = df_from_file.start_addr
        end_addr = worksheet.get_named_range(worksheet_title).end_addr
        # print(end_addr)
    except pygsheets.exceptions.RangeNotFound:
        # start_addr = (1, 1)
        end_addr = (1, len(HEADERS_FROM_FILE))
    finally:
        # df_from_file = worksheet.get_values(start=start_addr, end=end_addr, returnas='matrix')
        # df_from_file = pd.DataFrame(df_from_file[1:], columns=HEADERS_FROM_FILE)
        df_from_file = worksheet.get_as_df(has_header=True,
                                           index_column=None,
                                           start='A1',
                                           end=end_addr,
                                           numerize=True,
                                           empty_value=0,
                                           include_tailing_empty=True)
        df_from_file.columns = HEADERS_FROM_FILE
        # преобразование чисел с запятой для работы в Python в числа с точкой
    try:
        # локализаиця дата-фрейма для работы в python, если локализация гугл-таблицы 'Россия'
        if google_sheet.to_json()['properties']['locale'] == 'ru_RU':
            df_from_file['f_price'] = df_from_file['f_price'].astype(str).str.replace(',', '.').\
                fillna(df_from_file['f_price']).astype(float)
            df_from_file['f_price_old'] = df_from_file['f_price_old'].astype(str).str.replace(',', '.'). \
                fillna(df_from_file['f_price_old']).astype(float)
            df_from_file['f_min_price'] = df_from_file['f_min_price'].astype(str).str.replace(',','.').\
                fillna(df_from_file['f_min_price']).astype(float)
    except ValueError:
        print('Ошибка преобразования цен при чтении из файла')
    return df_from_file


def write_parsing_to_gsheet(spreadsheet_url, worksheet_title, df_merge):
    # print(id(df_merge))
    client = connection_api_gsheet()
    google_sheet = client.open_by_url(spreadsheet_url)
    worksheet = google_sheet.worksheet_by_title(worksheet_title)
    try:
        # очищаем на листе все значения в именнованном диапазоне
        # worksheet.get_named_range(worksheet_title).clear()

        # удаляем на листе именнованный диапазон
        worksheet.delete_named_range(worksheet_title)
        # полностью очищаем все значения на листе
        worksheet.clear()
    except:
        # если нет на листе именнованного диапазона, то полностью очищаем все значения на листе
        worksheet.clear()
    try:
        # добавляем на лист таблицу с результатом парсинга товаров
        # worksheet.append_table(values=values,  start='A1', overwrite=True)
        # df_merge = df_merge.infer_objects()
        # print(df_merge.info())

        # локализация гугл-таблицы Россия, то меняем точки на запятые в дробных числах
        if google_sheet.to_json()['properties']['locale'] == 'ru_RU':
            df_merge['p_price'] = df_merge['p_price'].astype(str).str.replace('.', ',').\
                fillna(df_merge['p_price']).astype(str)
            df_merge['p_price_old'] = df_merge['p_price_old'].astype(str).str.replace('.', ','). \
                fillna(df_merge['p_price_old']).astype(str)
            df_merge['f_min_price'] = df_merge['f_min_price'].astype(str).str.replace('.', ','). \
                fillna(df_merge['f_min_price']).astype(str)
    except ValueError:
        print('Ошибка преобразования цен при записи в файл')
    # print(df_merge.info())

    df_merge.columns = HEADERS
    worksheet.set_dataframe(
        df_merge,
        start='A1',
        copy_index=False,
        copy_head=True,
        extend=False,
        fit=True,
        escape_formulae=False
    )
    # добавляем именнованный диапазон по размерам таблиц
    worksheet.create_named_range(
        name=worksheet_title,
        start=(1,1),
        end=(df_merge.shape[0] + 1, df_merge.shape[1]),
        grange=''
    )
    # формируем словарь для форматирования листа через batch_update
    requests_for_batch_update = requests_to_googlesheet(
        worksheet.id,
        HEADERS.index('Статус'),
        HEADERS.index('Минимальная цена'))
    # print(requests_for_batch_update)
    client.sheet.batch_update(spreadsheet_id=google_sheet.id,
                              requests=requests_for_batch_update)

    # изменяем ширину столбцов автоматически по ширине значений
    worksheet.adjust_column_width(start=1, end=df_merge.shape[1], pixel_size=None)

    return print('Сохранили данные парсинга в файл', google_sheet.url)


def add_new_parsing(new_parsing):
    client = connection_api_gsheet()
    try:
        google_sheet = client.open_by_url(URL_GOOGLESHEET_SETTINGS)
        worksheet = google_sheet.worksheet_by_title(NAME_WORKSHEET_SETTINGS)
        c_range = worksheet.get_named_range(NAME_RANGE_SETTINGS).range
        data_for_parsing = worksheet.range(c_range, returnas='matrix')
        data_for_parsing.append(new_parsing)
        # очищаем на листе все значения в именнованном диапазоне
        worksheet.get_named_range(NAME_RANGE_SETTINGS).clear()
        # удаляем на листе именнованный диапазон
        worksheet.delete_named_range(NAME_RANGE_SETTINGS)
        # добавляем таблицу значений
        # worksheet.append_table(data_for_parsing, start='A1', end=None, dimension='ROWS', overwrite=True)
        worksheet.update_values(crange=(1, 1), values=data_for_parsing)
        # добавляем именнованный диапазон по размерам таблиц
        worksheet.create_named_range(
            name=NAME_RANGE_SETTINGS,
            start=(1, 1),
            end=(len(data_for_parsing), len(data_for_parsing[0])),
            grange=''
        )
        return True  # 'Данные успешно сохранены и парсинг активирован'
    except google_exceptions.TransportError:
        print('Нет подключения к Google-таблице')
        return False  # 'Возникла ошибка, попробуйте еще раз.'
    except google_HttpError:
        print('Нет доступа к Google-таблице')
        return False  # 'Возникла ошибка, попробуйте еще раз.'
    except pygsheets.exceptions.WorksheetNotFound:
        print('Такого листа не существует')
        return False  # 'Возникла ошибка, попробуйте еще раз.'
    except pygsheets.exceptions.RangeNotFound:
        print('Такого именнованного диапазоне не существует')
        return False  # 'Возникла ошибка, попробуйте еще раз.'
    except Exception:
        print('Что-то пошло не так')
        return False  # 'Возникла ошибка, попробуйте еще раз.'
    # print('data_for_parsing', data_for_parsing)


if __name__ == '__main__':
    print(load_settings_for_parsing())
    # print(write_parsing_to_gsheet('https://docs.google.com/spreadsheets/d/1Sx9INT-i8vexP6n2EtD524mybDG3tsppYqusinJHlTE/edit#gid=0',
                                 #'witerra'))
    # df_old = load_file_parsing_from_gsheet('https://docs.google.com/spreadsheets/d/1Sx9INT-i8vexP6n2EtD524mybDG3tsppYqusinJHlTE/edit#gid=0',
                                 # 'huggies')
    #print(df_old)