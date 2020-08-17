from bs4 import BeautifulSoup
# import csv
from datetime import datetime
from fake_useragent import UserAgent, FakeUserAgentError
# import os
import pandas as pd
import requests
import time
import googlesheets
import analytics


# from requests.models import Response


HEADERS_FOR_PARSING = (
    'id_product',
    'p_product',
    'p_brand',
    'p_price',
    'p_price_old',
    'p_url_product',
    'p_similar_id'
)


class Parser:
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()
        self.session.headers = {
            'user-agent': self.user_agent(),
            'accept-language': 'ru'
        }
        self.data_result = []

    def user_agent(self):
        for _ in range(5):
            try:
                ua = UserAgent()
                break
            except FakeUserAgentError:
                time.sleep(2)
        if ua:
            return ua.chrome
        else:
            return \
                'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1866.237 Safari/537.36'

    def load_page(self, params=''):
        try:
            print('Парсим ', self.url + params)
            self.result = self.session.get(url=self.url+params, timeout=5)
            self.result.raise_for_status()
            self.parse_page(self.result.text)
        except:
            print('Ошибка при чтении страницы ')
            # self.url, len(params), self.result.raise_for_status(), len(self.data_result))

    def parse_page(self, text: str):
        soup = BeautifulSoup(text, 'html.parser')
        container = soup.select('div.dtList.i-dtList.j-card-item')
        print('В работе', len(container))
        # container = soup.find ('div', {'class': 'dtList i-dtList j-card-item'}) # другой вариант
        for block in container:
            self.parse_block(block)
        # если пагинация сверху и снизу, то берем информацию из первого найденого блока
        container = soup.find(class_='pageToInsert').find(class_='pagination-next')
        # print(container) # для проверки кол-ва страниц
        if container:
            time.sleep(3)
            href = container.get('href')
            n_param = href.find('?')
            params = href[n_param:len(href)]
            # print(params)
            self.load_page(params)

    def parse_block(self, block):
        id_product, product, brand, price, price_old, url_product, similar_id = '', '', '', '', '', '', ''
        id_product = int(block['data-popup-nm-id'])
        # print(id_product)
        product = str(block.find('span', {'class': 'goods-name c-text-sm'}).text.strip())
        brand = block.find('strong', {'class': 'brand-name c-text-sm'}).text.replace('/', '').strip()
        price = float(''.join(block.find(class_='lower-price').text.split()).strip('тг.'))
        # или можно price = float(block.select_one('ins.lower-price').text.replace(u'\xa0', '').strip('тг.')))
        price_old = block.select_one('span.price-old-block')
        # если текущая цена без скидки, то старая цена равна цене без скидки
        if price_old:
            price_old = float(''.join(price_old.find_next('del').text.split()).strip('тг.'))
        else:
            price_old = price
        url_product = block.select_one('a.ref_goods_n_p').get('href')
        similar_id = block['data-nm-ids']

        data_now = datetime.now().strftime("%Y-%m-%d %H:%M")
        status_product = 'В наличии'
        min_price = price

        self.data_result.append(
            [
                id_product,
                product,
                brand,
                price,
                price_old,
                url_product,
                similar_id,
               # data_now,
               # status_product,
               # min_price
            ]
        )
        # self.data_result.append(
        #     ResultParsing(
        #         id_product=id_product,
        #         product=product,
        #         brand=brand,
        #         price=price,
        #         price_old=price_old,
        #         url_product=url_product,
        #         similar_id=similar_id
        #     )
        # )

        # writer.writerow(self.data_result)

    def parsing(self):
        self.load_page()


def parsing_from_settings():
    """

    :return: messages_for_notification # список сообщений для отправки согласно статусов товаров
    """
    success_parsing = 0
    messages_for_notification = {}  # список сообщений для отправки согласно статусов товаров
    data_for_parsing = googlesheets.load_settings_for_parsing()  # получаем настройки для парсинга
    all_parsing = len(data_for_parsing)
    for data in data_for_parsing:
        if data[4] == 'Активен':
            user_id = data[0]
            url = data[1]
            spreadsheet_url = data[2]
            worksheet_title = data[3]
            wb_parser = Parser(url)
            wb_parser.parsing()
            if len(wb_parser.data_result) != 0:
                df_from_parsing = pd.DataFrame(wb_parser.data_result, columns=HEADERS_FOR_PARSING)
                df_from_file = googlesheets.load_file_parsing_from_gsheet(spreadsheet_url, worksheet_title)
                df_merge = df_from_file.merge(df_from_parsing, how='outer', left_on='id_product', right_on='id_product')
                # проведение анализа статусов и формирование итоговой таблицы для загрузки
                df_merge = analytics.change_analysis(df_merge)
                if user_id in messages_for_notification:
                    messages_for_notification[user_id].append([
                        url,
                        spreadsheet_url,
                        worksheet_title,
                        analytics.status_for_message(df_merge)])
                else:
                    messages_for_notification[user_id] = []
                    messages_for_notification[user_id].append([
                        url,
                        spreadsheet_url,
                        worksheet_title,
                        analytics.status_for_message(df_merge)])
                # После следующей строки df_merge преобразуется
                # print(id(df_merge)) # ссылка на объект совпадает при обработке в функции ниже
                googlesheets.write_parsing_to_gsheet(spreadsheet_url, worksheet_title, df_merge)
                print('Готово! Спарсили', len(wb_parser.data_result))
                success_parsing += 1
            else:
                print('Что-то пошло не так')
    print(f'{success_parsing} из {all_parsing}')
    # print(messages_for_notification) # TODO сделать сортировку по ID пользователя, чтобы отпралять сообщения по порядку
    return messages_for_notification



if __name__ == '__main__':
    parsing_from_settings()
    # data_for_parsing = googlesheets.load_settings_for_parsing()
    # for data in data_for_parsing:
    #     if data[1]:
    #         url = data[1]
    #         spreadsheet_url = data[2]
    #         worksheet_title = data[3]
    #         wb_parser = Parser(url)
    #         wb_parser.parsing()
    #         df_from_parsing = pd.DataFrame(wb_parser.data_result, columns=HEADERS_FOR_PARSING)
    #         df_from_file = googlesheets.load_file_parsing_from_gsheet(spreadsheet_url, worksheet_title)
    #         df_merge = df_from_file.merge(df_from_parsing, how='outer', left_on='id_product', right_on='id_product')
    #         # df_merge.to_csv('result.csv', sep=';', encoding='cp1251')
    #         # проведение анализа статусов и формирование итоговой таблицы для загрузки
    #         df_merge = analytics.change_analysis(df_merge)
    #         # меняем в датафрейме заголовки столбцов для выгрузки в файл
    #         # df_merge.columns = HEADERS
    #         # df_merge.to_csv('result.csv', sep=';', encoding='cp1251')
    #         # wb_parser.data_result.insert(0, HEADERS)
    #         googlesheets.write_parsing_to_gsheet(spreadsheet_url, worksheet_title, df_merge)
    #         #path = os.path.join(os.getcwd(), 'result.csv') # текущий полный адрес для записи файла
    #         #print('Результат будет сохранен в файл', path)
    #         # with open(path, 'w', encoding='cp1251', newline='') as file:
    #         #     writer = csv.writer(file, delimiter=';')
    #         #     writer.writerow(HEADERS)
    #         #     for item in wb_parser.data_result:
    #         #         writer.writerow(item)
    #     # вариант с записью в файл каждой страницы
    #     # with open(path, 'w', encoding='cp1251', newline='') as file:
    #     #     writer = csv.writer(file, delimiter=';')
    #     #     writer.writerow(HEADERS)
    #     #     wb_parser.parsing()
    #         if len(wb_parser.data_result) == 0:
    #             print('Что-то пошло не так')
    #         else:
    #         # print(wb_parser.data_result)
    #             print('Готово! Спарсили', len(wb_parser.data_result))



