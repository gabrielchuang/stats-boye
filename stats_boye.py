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

chart_commands = []
admin_commands = ['add_ignored_channel', 'set_color', 'refresh_users', 'refresh_messages', 'clear_messages_table', 'refresh_channel', 'refresh_roles', 'refresh_emojis', 'add_bot', 'remove_bot', 'add_admin', 'remove_admin', 'sudo']
misc_commands = ['set_my_color']


'''
conn = sqlite3.connect("information.db")
c = conn.cursor()
c.execute('SELECT user_ID FROM users WHERE privs=2')
auth_admins = [x[0] for x in list(c.fetchall())]
c.close()
conn.close()
'''

auth_admins = open('admins.csv').read().strip().split(',')
print(auth_admins)


async def run_chart_command(message):
	'''await message.add_reaction('⚙️')

	chart_type = 
	splitby = #e.g. split pie segments by channel, split line/bar graphs by user

	channels = parse_channels
	await message.remove_reaction('⚙️', message.guild.me)
	if success:
		await message.add_reaction("📈")'''
	pass

@client.event
async def on_message(message): #currently very basic, just for testing (for now)
	if any([(cc+x) in message.content for x in admin_commands]):
		if str(message.author.id) in auth_admins:
			await run_admin_command(message, client)
		else:
			await message.add_reaction("😡")
	elif any([(cc+x) in message.content for x in chart_commands]):
		await run_chart_command(message)

	elif "!parse_test" in message.content and "bot-testing" in str(message.channel):
		try:
			c = Query(message, client)
			await message.channel.send(str(c.filters))
		except InvalidQuery as s:
			await message.channel.send(s)
	elif "!query_test" in message.content and "bot-testing" in str(message.channel):
		try:
			c = Query(message, client)
			(where, args) = c.sql_filter_string()
			inner_join = c.sql_joins_string()
			await message.channel.send('`WHERE true' + str(where) + '`\n' +  str(args) + '\n' + str(inner_join))
		except InvalidQuery as s:
			await message.channel.send(s)
	elif "!pt" in message.content and "bot-testing" in str(message.channel):
		try:
			c = PieChart(message, client)
			c.construct_piechart()
			c.create_embed()
			await c.send()
		except InvalidQuery as s:
			await message.channel.send(s)
	elif "!bt" in message.content and "bot-testing" in str(message.channel):
		try:
			c = BarChart(message, client)
			c.construct_barchart()
			c.create_embed()
			await c.send()
		except InvalidQuery as s:
			await message.channel.send(s)
	elif "!tt" in message.content and "bot-testing" in str(message.channel):
		try:
			c = TimeChart(message, client)
			c.construct_timechart()
			c.create_embed()
			await c.send()
		except InvalidQuery as s:
			await message.channel.send(s)
	elif "!wcd" in message.content and "bot-testing" in str(message.channel):
		try:
			c = WordCountDistribution(message, client)
			c.construct_wordCountDistributionChart()
			c.create_embed()
			await c.send()
		except InvalidQuery as s:
			await message.channel.send(s)
	elif any([(cc+x) in message.content for x in misc_commands]):
		await run_misc_command(message, client)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

	for server in client.guilds:
		if "CMU" in str(server):
			await refresh_channels(server)

client.run(token)
