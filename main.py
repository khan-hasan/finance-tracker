import argparse
import collections
import csv
from datetime import datetime
import os
from pprint import pprint

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


def categorize_transaction(transaction):
    with open('categories_dict.csv', 'r+', newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        writer = csv.DictWriter(csv_file, fieldnames=['key word', 'category'])

        categories_set = set()
        for row in reader:
            categories_set.add(row['category'])
            if row['key word'].lower() in transaction['Description'].lower():
                return row['category']

        print('====================')
        print('\n', pprint(dict(transaction)))
        category = input_category_from_dict(categories_set, writer)
        return category


def process_transactions(financial_institutions):
    # Combine all statements from all banks into single DataFrame
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
                            row)
                        transaction['date'] = datetime.strptime(
                            row['Posting Date'], '%m/%d/%Y').strftime('%Y-%m-%d')
                        transaction['description'] = row['Description']
                        transaction['amount'] = float(row['Amount'])
                        transaction['balance'] = float(row['Balance'])

                    elif fin_inst.lower() == 'unify':
                        transaction['account'] = row['Account Number'].split(
                            '-')[0]
                        transaction['date'] = datetime.strptime(
                            row['Post Date'], '%m/%d/%Y').strftime('%Y-%m-%d')
                        transaction['description'] = row['Description']
                        transaction['amount'] = float(row['Credit']) if row.get(
                            'Credit') else -float(row['Debit'])
                        transaction['category'] = categorize_transaction(
                            row)
                        transaction['balance'] = float(row['Balance'])

                    combined_transactions.append(transaction)

    with open('all_transactions.csv', 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
            'account', 'date', 'description', 'amount', 'category', 'balance'])
        writer.writerows(combined_transactions)

        master_statement = pd.read_csv('all_transactions.csv', names=[
            'account', 'date', 'description', 'amount', 'category', 'balance'], parse_dates=['date'])

        return master_statement


def analyze(statement):
    pd.set_option('max_rows', None)

    # Sort transactions by date
    df = statement.sort_values(['date'], ascending=False)
    df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y %B')

    # Determine balance per month
    account_balances = df.sort_values(
        'date').groupby(['account', 'month'], as_index=False).tail(1)
    total_balance = account_balances.groupby('month', as_index=False)[
        'balance'].sum()

    # Determine total spending per month per category
    df = df.groupby(['month', 'category']).sum().reset_index()
    df = pd.pivot_table(df, values='amount', index=[
        'month'], columns='category').reset_index()

    # Set date as index
    df.index = pd.to_datetime(df['month']).dt.strftime('%Y %B')
    df.index.name = 'date'
    df.columns.name = None

    # Combine data into a single DataFrame
    df = pd.merge(df, total_balance, left_on='month', right_on='month')

    # Determine net profit per month
    # TODO: dynamically retrieve these column names
    COLS = [
        'ATM',
        'bills',
        'car',
        'deen',
        'dining',
        'education',
        'entertainment',
        'groceries',
        'health',
        'home',
        'income',
        'internal transfer',
        'rent',
        'shopping',
        'taxes',
        'travel',
        'uncategorized'
    ]
    df['net profit'] = df[COLS].sum(axis=1)

    # TODO: Order data by month
    df.to_excel("output.xlsx")

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze spending across accounts.')
    parser.add_argument('action', type=str, choices=[
                        'analyze', 'edit'], help='an action for the analyzer')
    args = parser.parse_args()

    if args.action == 'analyze':
        statement = process_transactions(['chase', 'unify'])
        df = analyze(statement)

    elif args.action == 'edit':
        pass

    else:
        raise Exception
