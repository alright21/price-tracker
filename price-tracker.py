
'''
Project built starting from https://oxylabs.io/blog/how-to-build-a-price-tracker


TODO:
- history: create price history for each game
- refactor: use relational databases
'''

import pandas as pd
import requests
from bs4 import BeautifulSoup
from price_parser import Price
from datetime import datetime
import logging
from telegram import Update, constants
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler
from prettytable import PrettyTable

## Configuration files
from config import TELEGRAM_TOKEN

PRODUCT_URL_CSV = "data/products.csv"
SAVE_TO_CSV = True
PRICES_CSV = "data/prices.csv"


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

def get_urls(csv_file):
    df = pd.read_csv(csv_file)
    return df

def process_products(df):
    updated_products = []
    for product in df.to_dict("records"):
        product["amazon_price"] = get_price_amazon(get_response(product["amazon"]))
        product["dungeondice_price"] = get_price_dungeondice(get_response(product["dungeondice"]))
        product["feltrinelli_price"] = get_price_feltrinelli(get_response(product["feltrinelli"]))
        product["time"] = datetime.now()
        updated_products.append(product)
    return pd.DataFrame(updated_products)

def get_response(url):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0'}
    if not pd.isna(url):
        response = requests.get(url, headers=headers)
        # logging.warning(str(response.status_code)+ ' ' + url)
        return response.text
    else:
        return ''

def get_price_amazon(html):
    if html != '':
        soup = BeautifulSoup(html, "lxml")
        el = soup.select_one(".a-offscreen")
        price = Price.fromstring(el.text)
        return price.amount_float
    else:
        return 0.0

def get_price_dungeondice(html):
    if html != '':
        soup = BeautifulSoup(html, "lxml")
        el = soup.select_one(".display-price")
        price = Price.fromstring(el.text)
        return price.amount_float
    else:
        return 0.0
    
def get_price_feltrinelli(html):
    if html != '':
        soup = BeautifulSoup(html, "lxml")
        el = soup.select_one(".cc-buy-box")
        el = el.select_one(".cc-price")
        price = Price.fromstring(el.text)
        return price.amount_float
    else:
        return 0.0

'''
Adds a new game, if the game exists, choose the urls to add
'''

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.args[0]
    website = context.args[1]
    url = context.args[2]

    logging.info(name)
    df = get_urls(PRODUCT_URL_CSV)
    condition = df['name'] == name
    result = df.loc[condition]

    if len(result) == 0:
        new_item = pd.DataFrame({'name':name, website:url}, index=[0])
        df = pd.concat([df, new_item])

    else:
        # logging.info(result)
        df.loc[condition, website] = url

    df.to_csv(PRODUCT_URL_CSV, mode="w", index=None)

async def list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_urls(PRODUCT_URL_CSV)

    table = PrettyTable()
    table.field_names = ["Name"]
    table.align["Name"] = 'l'

    for _, row in df.iterrows():
        table.add_row([' '.join(word.capitalize() for word in row["name"].replace('_', ' ').split())])

    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="```\n" + table.get_string() + "\n```"
        , parse_mode= 'MarkdownV2'
        )

async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.debug('UPDATE CALLED')
    df = get_urls(PRODUCT_URL_CSV)
    df_updated = process_products(df)
    if SAVE_TO_CSV:
        df_updated.to_csv(PRICES_CSV, index=False, mode="w")
    
    table = PrettyTable()

    table.field_names = ["Name","Amazon","DungeonDice","Feltrinelli"]
    table.align["Name"] = 'l'
    table.align["Amazon"] = 'r'
    table.align["DungeonDice"] = 'r'
    table.align["Feltrinelli"] = 'r'
    for _, row in df_updated.iterrows():
        table.add_row([' '.join(word.capitalize() for word in row["name"].replace('_', ' ').split()),row['amazon_price'],row['dungeondice_price'],row['feltrinelli_price']])

    message = "🎲    *Updated Prices* \- `" + str(datetime.now()) +"`\n\n```\n" + table.get_string() + "\n```"
    logging.debug("\n" + message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message, 
        parse_mode= 'MarkdownV2'
        )

def compare():
    logging.debug("Compare function called")

def history():
    logging.debug("History function called")

def reset():
    logging.debug("rest function called")


def initialize_telegram_bot():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    add_game_handler = CommandHandler('add', add)
    list_handler = CommandHandler('list', list)
    update_handler = CommandHandler('update', update)   

    application.add_handler(add_game_handler)
    application.add_handler(list_handler)
    application.add_handler(update_handler)

    application.run_polling()
def main():

    initialize_telegram_bot()


if __name__ == "__main__":
    main()