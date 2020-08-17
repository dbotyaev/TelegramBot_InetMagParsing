import pandas as pd
from datetime import datetime, timedelta


UNAVAILABLE = 'Недоступен'
NOVELTY = 'Новинка'
IN_STOCK = 'В наличии'
TO_BUY = 'К покупке'
MONITOR_RECEIPT = 'Отслеживать'
RECEIPT = 'Поступление'


def edit_result_analysis(df_merge):
    """ формирование итогового датафрема """
    # объединяем значения из разных столбцов в один в зависимости от условий
    df_merge.loc[df_merge['p_product'].isnull(), 'p_product'] = df_merge['f_product']
    df_merge.loc[df_merge['p_brand'].isnull(), 'p_brand'] = df_merge['f_brand']
    df_merge.loc[df_merge['p_price'].isnull(), 'p_price'] = df_merge['f_price']
    df_merge.loc[df_merge['p_price_old'].isnull(), 'p_price_old'] = df_merge['f_price_old']
    df_merge.loc[df_merge['p_url_product'].isnull(), 'p_url_product'] = df_merge['f_url_product']
    df_merge.loc[df_merge['p_similar_id'].isnull(), 'p_similar_id'] = df_merge['f_similar_id']
    df_merge.loc[df_merge['f_status_product'] != UNAVAILABLE, 'f_data_parsing'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    # удаляем ненужные столбцы
    df_merge.drop(['f_product', 'f_brand', 'f_price', 'f_price_old', 'f_url_product', 'f_similar_id'], axis=1, inplace=True)
    # меняем порядок столбцов под необходимую структуру
    df_merge = df_merge[
        [
            'id_product',
            'p_product',
            'p_brand',
            'p_price',
            'p_price_old',
            'p_url_product',
            'p_similar_id',
            'f_data_parsing',
            'f_status_product',
            'f_min_price'
        ]
    ]
    return df_merge

def change_analysis(df_merge):
    # ВАЖНО! Порядок проверки должен соблюдаться

    # проверяем товары со статусом 'Недоступен' и если в новом парсинге 'p_product' непустой,
    # то меняем статус на 'В наличии'
    df_merge.loc[
        (df_merge['f_status_product'] == UNAVAILABLE) &
        (df_merge['p_product'].notnull()),
        'f_status_product'] = IN_STOCK

    # проверяем товары со статусом 'Отслеживать' и если в новом парсинге 'p_product' непустой,
    # то меняем статус на 'Поступление'
    df_merge.loc[
        (df_merge['f_status_product'] == MONITOR_RECEIPT) &
        (df_merge['p_product'].notnull()),
        'f_status_product'] = RECEIPT

    # приводим столбец с датами к формату Дата
    df_merge['f_data_parsing'] = pd.to_datetime(df_merge['f_data_parsing'], format="%Y-%m-%d %H:%M")

    # в новый столбец 'f_data_parsing_days' записываем разницу в днях timedelta.days - НЕ ПОТРЕБОВАЛОСЬ
    # df_merge['f_data_parsing_days'] = (datetime.now() - df_merge['f_data_parsing']).dt.days
    # все NaN в столбце 'f_data_parsing_days' меняем на 0, но работает и без него
    # df_merge['f_data_parsing_days'] = df_merge['f_data_parsing_days'].fillna(0)

    # отбираем пустые значения в поле 'p_product'
    # и меняем 'f_status_product' на 'Недоступен', кроме статуса 'Отслеживать'
    # т.е. те позиции, которые отсутствуют в парсинге
    df_merge.loc[
        (df_merge['p_product'].isnull()) & (df_merge['f_status_product'] != MONITOR_RECEIPT),
        'f_status_product'] = UNAVAILABLE

    # отбираем 'f_status_product' со значением 'Новинка' или 'К покупке',
    # если 'f_min_price' минимальная цена > 0, то меняем статус на 'В наличии'
    df_merge['f_min_price'] = df_merge['f_min_price'].fillna(0)
    try:
        df_merge.loc[
            ((df_merge['f_status_product'] == NOVELTY) | (df_merge['f_status_product'] == TO_BUY)) &
            (df_merge['f_min_price'] > 0),
            'f_status_product'] = IN_STOCK
    except TypeError:
        print('Ошибка в данных при анализе статусов Новинка => В наличии')

    # отбираем пустые значения в поле 'f_status_product' и меняем его на 'Новинка',
    # т.е. те позиции, которые отсутствуют в предыдущем файле парсинга
    df_merge.loc[df_merge['f_status_product'].isnull(), 'f_status_product'] = NOVELTY

    # отбираем позиции с текущей ценой менее минимальной цены и кроме статуса 'Недоступен' и кромер 'Поступление'
    # и устанавливаем статус 'К покупке'
    df_merge.loc[
        (df_merge['p_price'] <= df_merge['f_min_price']) &
        ((df_merge['f_status_product'] != UNAVAILABLE) | (df_merge['f_status_product'] != RECEIPT)),
        'f_status_product'] = TO_BUY
    df_merge = edit_result_analysis(df_merge)
    return df_merge


def status_for_message(df):
    # получаем объект Series с кол-вом статусов во итоговом парсинге
    df = df.groupby('f_status_product')['f_status_product'].count().to_dict()
    # преобразуем в словарь, где индексами являются статусы
    # df.to_dict()
    print(df)
    # тесты
    # df = df.reset_index(name='count')
    # df = df.to_dict('records')
    # df = df.to_frame()
    # df = df.values.tolist()
    # df = df.reset_index(name='ind')
    # print(type(df))
    # print(df)
    # print('К покупк' in df)
    # print(df['f_status_product'].unique().tolist())

    return df