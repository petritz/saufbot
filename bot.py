#!/bin/python3

import telebot
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

token = os.environ.get('TOKEN')
bot = telebot.TeleBot(token, parse_mode=None)

conn = psycopg2.connect(os.environ.get('CONN'))

welcome_message = "Ich trink nicht viel, aber saufen tu ich umso lieber."
log_information_format = "[Getränk] [Menge in L: 0.5]"
create_information_format = "/create [Getränk] [Alkohol-Volumsprozent] [Default in L]"


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
  bot.reply_to(message, welcome_message)


@bot.message_handler(commands=['userstat'])
def send_stat(message):
  c = conn.cursor()
  username = message.from_user.username
  c.execute("select sum(alcohol_content) from stat where username = '%s'" % (username))
  row = c.fetchone()
  total_alcohol = row[0]

  c.execute("select (select sum(alcohol_content) from stat where username = '%s') / sum(alcohol_content) from stat" % (username))
  row = c.fetchone()
  if row and row[0]:
    total_share = row[0] * 100
  else:
    total_share = 0

  bot.reply_to(message, "%s hat %.0f%% des gesamten Alkohols konsumiert, das sind %.2fg reiner Alkohol" % (username, total_share, total_alcohol))
  c.close()


@bot.message_handler(commands=['stat'])
def send_total_stat(message):
  c = conn.cursor()
  c.execute("select username, sum(alcohol_content), (sum(alcohol_content) / (select sum(alcohol_content) from stat)) * 100 from stat group by username order by sum desc;")
  rows = c.fetchall()
  result = ""

  rank = 1
  for row in rows:
    result += "%d. %s: %.0f%% (%.2fg)\n" % (rank, row[0], row[2], row[1])
    rank += 1

  bot.send_message(message.chat.id, result)
  c.close()


@bot.message_handler(commands=['create'])
def create(message):
  line = message.text
  splitted = line.split(" ")
  if not splitted:
    return

  if len(splitted) != 4:
    bot.reply_to(message, f"Bitte im Format {create_information_format} angeben")
    return

  try:
    name = splitted[1]
    percent = float(splitted[2])
    volume = float(splitted[3])
  except ValueError:
    bot.reply_to(message, f"Bitte im Format {create_information_format} angeben")

  c = conn.cursor()
  c.execute("insert into alcohol (name, percent, volume) values ('%s', %f, %f)" % (name, percent, volume))
  bot.reply_to(message, "Getränk %s wurde erfolgreich erstellt." % (name))
  c.close()


@bot.message_handler(func=lambda m: True)
def echo_all(message):
  line = message.text
  splitted = line.split(" ")
  if not splitted:
    return

  if len(splitted) < 1 or len(splitted) > 2:
    bot.reply_to(message, f"Bitte im Format {log_information_format} angeben")
    return

  username = message.from_user.username

  if(len(splitted) == 1):
    drink = line.lower()
  else:
    drink = splitted[0].lower()
  
  c = conn.cursor()
  c.execute("select * from alcohol where lower(name) like '%%%s%%'" % drink)
  row = c.fetchone()
  if not row:
    # bot.reply_to(message, "Getränk nicht gefunden.")
    return

  if(len(splitted) == 2):
    try:
      volume = float(splitted[1])
    except ValueError:
      bot.reply_to(message, f"Bitte im Format {log_information_format} angeben")
      return
  else:
    volume = row[3]

  percent = row[2]

  # rho = 0.785g/ml
  alcohol = volume * (percent / 100) * 0.785
  c.execute("insert into stat (alcohol_id, volume, alcohol_content, username) values (%d, %f, %f, '%s')" % (row[0], volume, alcohol, username))
  conn.commit()
  c.close()

  bot.reply_to(message, "Getränkt vermerkt: %s (%.2fL)" % (row[1], volume) )

bot.polling()
