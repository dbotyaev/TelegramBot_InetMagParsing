from analytics import UNAVAILABLE, NOVELTY, IN_STOCK, TO_BUY, RECEIPT, MONITOR_RECEIPT


def requests_to_googlesheet(worksheet_id, status_index, min_price_index):

    # очистка проверки данных заданным условиям на всем листе
    set_data_validation_clear = {'setDataValidation':
                                     {'range':
                                          {'sheetId': worksheet_id}}}

    # Очищаем базовый фильтр на листе
    set_basic_filter_clear = {'clearBasicFilter':
                                  {'sheetId': worksheet_id}}

    # установка в Google-таблице в столбце со статусами проверки данных значений ячеек из списка
    # с целью выбора только установленных значений
    set_data_validation_status = {'setDataValidation':
                               {'range':
                                    {'sheetId': worksheet_id,
                                     'startRowIndex': 1,
                                     # 'endRowIndex': 1,
                                     'startColumnIndex': status_index,
                                     'endColumnIndex': status_index+1},
                                'rule':
                                    {'condition':
                                         {'type': 'ONE_OF_LIST',
                                          'values': [
                                              {'userEnteredValue': NOVELTY},
                                              {'userEnteredValue': IN_STOCK},
                                              {'userEnteredValue': UNAVAILABLE},
                                              {'userEnteredValue': RECEIPT},
                                              {'userEnteredValue': TO_BUY},
                                              {'userEnteredValue': MONITOR_RECEIPT}]},
                                     'inputMessage': 'Введите значение из списка',
                                     'showCustomUi': True,
                                     'strict': True}}}

    set_data_validation_min_price = {'setDataValidation':
                                      {'range':
                                           {'sheetId': worksheet_id,
                                            'startRowIndex': 1,
                                            # 'endRowIndex': 1,
                                            'startColumnIndex': min_price_index,
                                            'endColumnIndex': min_price_index + 1},
                                       'rule':
                                           {'condition':
                                                {'type': 'NUMBER_GREATER_THAN_EQ',
                                                 'values': [
                                                     {'userEnteredValue': '0'},]},
                                            'inputMessage': 'Значения должны быть >= 0',
                                            'showCustomUi': True,
                                            'strict': True}}}

    # Создаем базовый фильтр на листе
    set_basic_filter = {'setBasicFilter':
                            {'filter':
                                 {"range":
                                      {"sheetId": worksheet_id}}}}

    # Закрепление 1 строки
    frozen_row_count_1 = {'updateSheetProperties':
                                   {'properties':
                                        {'sheetId': worksheet_id,
                                         'gridProperties':
                                             {'frozenRowCount': 1}},
                                    'fields': 'gridProperties.frozenRowCount'}}
    requests_for_batchupdate = [
        set_basic_filter_clear,
        # set_data_validation_clear,
        frozen_row_count_1,
        set_basic_filter,
        set_data_validation_status,
        set_data_validation_min_price
    ]

    return requests_for_batchupdate
