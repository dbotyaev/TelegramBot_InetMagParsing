from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgentError
from googlesheets import connection_api_gsheet
# from settings import SERVICE_ACCOUNT_FILE
# import pygsheets
import requests
import time

# для обработки ошибок
from google.auth import exceptions as google_exceptions
from googleapiclient.errors import HttpError as google_HttpError
from pygsheets import exceptions as gsheet_expections


def user_agent():
    for _ in range(5):
        try:
            ua = UserAgent()
            break
        except FakeUserAgentError:
            time.sleep(2)
    if ua:
        return ua.chrome
    else:
        return 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) ' \
               'Chrome/34.0.1866.237 Safari/537.36'


def validation_url_for_parser(url):
    """
    проверка ссылки для парсинга
    выдает кол-во товаров для парсинга на первой странице,
    либо False, если страница не доступна
    """
    session = requests.Session()
    session.headers = {
        'user-agent': user_agent(),
        'accept-language': 'ru'
    }
    try:
        result = session.get(url=url, timeout=5)
        result.raise_for_status()
        soup = BeautifulSoup(result.text, 'html.parser')
        container = soup.select('div.dtList.i-dtList.j-card-item')
        return len(container)
    except:
        return False # 'Ошибка при чтении страницы'


def validation_spreadsheet_url(url):
    """
    проверка ссылки google-таблицы
    """
    try:
        client = connection_api_gsheet()
        google_sheet = client.open_by_url(url)
        # print(client.drive.list_permissions(google_sheet.id))
        # print(google_sheet.to_json())
        # print(google_sheet.url)
        return 'ok', google_sheet.url
    except google_exceptions.TransportError:
        print('Нет подключения к Google-таблице')
        return 'error url', ''
    except google_HttpError:
        print('Нет доступа к Google-таблице')
        return 'error access', ''
    except gsheet_expections.NoValidUrlKeyFound:
        print('Неправильная ссылка на Google-таблицу')
        return 'error address', ''
    # except:
    #     return False
    # worksheet = google_sheet.worksheet_by_title(NAME_WORKSHEET_SETTINGS)


def validation_worksheet_title(url, title):
    """
    Проверка существования листа в Google-таблице и его создание, если не существует
    :param url: ссылка на Google-таблицу
    :param title: имя листа для сохранения результата
    :return:
    """
    try:
        client = connection_api_gsheet()
        google_sheet = client.open_by_url(url)
        worksheet = google_sheet.worksheet_by_title(title)
        # print('worksheet.url', worksheet.url)
        return 'ok', worksheet.url  # книга открылась, лист существует
    except gsheet_expections.WorksheetNotFound:
        print('Такого листа не существует')
        try:
            google_sheet.add_worksheet(title)
            worksheet = google_sheet.worksheet_by_title(title)
            return 'ok', worksheet.url
        except google_HttpError:
            print('Нет доступа к Google-таблице')
            # TODO  Имя нового листа в Google_таблице в другой раскладке - не дает создать новый лист. Сделать проверку
            return 'error access', ''
    except:
        return False, ''
