import discord
import time
import sqlite3
import datetime
import pandas as pd 
import numpy as np 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
from queries import *
from administrative import *
from charts import *
from miscellany import *

token = open('token.txt').read()
client = discord.Client()
plt.close('all')

cc = open('command_character.txt').read()[0]# command character

banned_channels = open('banned_channels.csv').read().split(',')

chart_commands = ['bar', 'pie', 'time', 'randomquote', 'rq', 'about', 'aboutme', 'wordcloud', 'cloud']
admin_commands = ['add_ignored_channel', 'set_color', 'refresh_users', 'refresh_messages', 'clear_messages_table', 'refresh_channel', 'refresh_roles', 'refresh_emojis', 'add_bot', 'remove_bot', 'add_admin', 'remove_admin', 'sudo', 'add_bot_channel', 'initialize_server']
misc_commands = ['set_my_color', 'basics', 'misc', 'admin', 'filters', 'cs', 'cheatsheet', 'help', 'statshelp']

auth_admins = open('admins.csv').read().strip().split(',')
print(auth_admins)

async def run_query(message, client):
	cc = open('command_character.txt').read()[0] # command character
	await message.add_reaction('⚙️')
	try:
		if cc+'pie' in message.content:
			c = PieChart(message, client)
			c.construct_piechart()
			c.create_embed()
			await c.send()
		elif cc+'bar' in message.content:
			c = BarChart(message, client)
			c.construct_barchart()
			c.create_embed()
			await c.send()
		elif cc+'time' in message.content:
			c = TimeChart(message, client)
			c.construct_timechart()
			c.create_embed()
			await c.send()
		elif cc+"randomquote" in message.content or cc+"rq" in message.content:
			c = RandomQuote(message, client)
			await c.send()
		elif cc+"about" in message.content:
			c = About(message, client)
			await c.send()
		elif cc+"wordcloud" in message.content or cc+"cloud" in message.content :
			c = MessageCloud(message, client)
			c.create_embed()
			await c.send()
		success = True
	except InvalidQuery as s:
			await message.channel.send(s)
			success = False
	except:
		await message.remove_reaction('⚙️', message.guild.me)
		await message.add_reaction("❌")
		raise

	await message.remove_reaction('⚙️', message.guild.me)
	if success:
		await message.add_reaction("📈")
	else: 
		await message.add_reaction("❌")
	return success 

@client.event
async def on_message(message):
	bot_channels = open('bot-channels.csv').read().strip().split(',')

	if str(message.channel.id) in bot_channels and message.author != message.guild.me:
		if any([(cc+x) in message.content for x in admin_commands]):
			if str(message.author.id) in auth_admins:
				await run_admin_command(message, client)
			else:
				await message.add_reaction("😡")
		elif any([(cc+x) in message.content for x in chart_commands]):
			await run_query(message, client)
		elif any([(cc+x) in message.content for x in misc_commands]):
			await run_misc_command(message, client)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

client.run(token)
