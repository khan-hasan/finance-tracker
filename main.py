import collections
import csv
from datetime import datetime
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


pd.set_option('display.float_format', lambda x: '%.2f' % x)


def input_category_from_dict(dict_items, writer):
    list_dict = list(dict_items)
    for i, item in enumerate(list_dict, 1):
        print(f'\n{i}. {item}')
    word = input('\nEnter key word: ')
    user_input = input('enter a category number, or enter a new category: ')
    try:
        category = list_dict[int(user_input)-1]
    except ValueError:
        category = user_input
    if not word in dict_items:
        writer.writerow({'key word': word, 'category': category})
    return category


def categorize_transaction(trans_description, amount):
    with open('categories_dict.csv', 'r+', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        writer = csv.DictWriter(csv_file, fieldnames=['key word', 'category'])

        categories_set = set()
        for row in reader:
            categories_set.add(row['category'])
            if row['key word'].lower() in trans_description.lower():
                return row['category']

        print('====================')
        print('\n', trans_description, amount)
        category = input_category_from_dict(categories_set, writer)
        return category


def process_transactions(financial_institutions):
    # Load statements and combine into a single DataFrame per each financial institution
    combined_transactions = []
    for fin_inst in financial_institutions:
        statement_dir = f'input_statements/{fin_inst}'
        statement_files = os.listdir(statement_dir)

        for statement_file in statement_files:
            with open(f'{statement_dir}/{statement_file}', 'r') as csv_file:
                statement = csv.DictReader(csv_file)

                for row in statement:
                    transaction = collections.OrderedDict()

                    if fin_inst.lower() == 'chase':
                        transaction['account'] = statement_file.split('_')[0]
                        transaction['category'] = categorize_transaction(
                            row['Description'], row['Amount'])
                        transaction['date'] = datetime.strptime(
                            row['Posting Date'], '%m/%d/%Y').strftime('%Y-%m-%d')
                        transaction['description'] = row['Description']
                        transaction['amount'] = float(row['Amount'])
                        transaction['balance'] = row['Balance']

                    elif fin_inst.lower() == 'unify':
                        transaction['account'] = row['Account Number'].split(
                            '-')[0]
                        transaction['date'] = datetime.strptime(
                            row['Post Date'], '%m/%d/%Y').strftime('%Y-%m-%d')
                        transaction['description'] = row['Description']
                        transaction['amount'] = row['Credit'] if row.get(
                            'Credit') else -float(row['Debit'])
                        transaction['category'] = categorize_transaction(
                            row['Description'], transaction['amount'])
                        transaction['balance'] = row['Balance']

                    combined_transactions.append(transaction)

    with open('all_transactions.csv', 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
                                'account', 'date', 'description', 'amount', 'category', 'balance'])
        writer.writerows(combined_transactions)

        master_statement = pd.read_csv('all_transactions.csv', names=[
            'account', 'date', 'description', 'amount', 'category', 'balance'], parse_dates=['date'])
        # master_statement['date'] = pd.to_datetime(
        #     master_statement['date'], format='%m/%d/%y')
        # print(master_statement)
        return master_statement


def sum_by_category(statement):
    pd.set_option('max_rows', None)

    # for verifying that transactions are categorized correctly
    df = statement.sort_values(['category', 'description'])

    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y %B')

    df = df.groupby(['date', 'category']).agg(
        {'amount': ['sum']}).reset_index()

    df = pd.pivot_table(df, values='amount', index=[
                        'date'], columns='category').reset_index()

    df.index = pd.to_datetime(df['date'], format='%Y %B')
    df = df.sort_index()

    # Remove top level of columns in column hierarchy
    df.columns = df.columns.get_level_values(1)

    print(df)

    # Draw graph of finances per category per month
    # df.plot(x='date', y='sum', kind='bar')
    # plt.show()

    import pdb
    pdb.set_trace()

    # Draw graph of net income per month
    df['total'] = df[['ATM', 'bills', 'car', 'deen', 'rent',
                      'shopping', 'taxes', 'travel', 'uncategorized']].sum(axis=1)

    # Draw graph of total profit per month
    df.plot(x='', y='total', kind='bar')
    plt.show()

    return df


if __name__ == '__main__':
    statement = process_transactions(['chase', 'unify'])
    df = sum_by_category(statement)
