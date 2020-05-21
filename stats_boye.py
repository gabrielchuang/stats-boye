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
from queries_requests import *
from refreshes_updates import *

token = open('token.txt').read()
client = discord.Client()
plt.close('all')

cc = open('command_character.txt').read()[0]# command character

banned_channels = open('banned_channels.csv').read().split(',')
chart_commands = []
admin_commands = ['add_ignored_channel', 'set_color', 'refresh_users', 'refresh_messages', 'clear_messages_table', 'refresh_channel', 'refresh_roles', 'refresh_emojis']
auth_admins = open('admins.csv').read().strip().split(',')

print(auth_admins)



'''
occurrences of matthew saying 'bar' vs ezekiel saying 'bar' in bot-coms over time, between jan 1 and jan 30:
!time --splitby user @matt @ezek --filter #bot-coms `bar` --date 1-1-2020 1-30-2020 --granularity month 
!time --splitby user user:matt user:ezek --filter #bot-coms `bar` --date 1-1-2020 1-30-2020 --granularity month 
!time --splitby user userid:12345 userid:12345 --filter #bot-coms `bar` --date 1-1-2020 1-30-2020 --granularity month 

relative channel activity over time: gen vs finelit
!time --splitby channel #gen #finelit --date 1-1-2020 1-30-2020

weeb activity over time
!time --filter @weebs 
!time --filter role:weebs

piechart - channels where 'ward' is said the most by ezek or jocel
!pie --splitby channel --filter `ward` @ezek @octi 
piechart - most common talkers in #gen
!pie --splitby user --filter #gen 

standard pie
!pie --splitby channel --filter @whoever

regex? 
proportions # limit to people with > x msgs

'''



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
			# invalid perms!
			await message.add_reaction("😡")
	elif any([(cc+x) in message.content for x in chart_commands]):
		await run_chart_command(message)
	elif "!parse_test" in message.content and "ezekiel" in str(message.author):
		try:
			c = Query(message, client)

#			c = Query.parse_channels(message, Query.get_channel_ids(message.guild), client)
#			msg = 'channels: ' + ' '.join([x.name for x in c])
#
#			u = Query.parse_users(message, Query.get_user_ids(message.guild), client)
#			msg += '\nusers: ' + ' '.join([x.name for x in u])
#
#			u = Query.parse_roles(message, Query.get_role_ids(message.guild), client)
#			msg += '\nroles: ' + ' '.join([x.name for x in u])

			await message.channel.send(str(c.filters))
		except InvalidQuery as s:
			await message.channel.send(s)


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

	for server in client.guilds:
		if "CMU" in str(server):
			await refresh_channels(server)

client.run(token)
