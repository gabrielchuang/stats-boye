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

token = open('token.txt').read()
client = discord.Client()
plt.close('all')

banned_channels = open('banned_channels.csv').read().split(',')

print(banned_channels)

def refresh_users(guild): 
	pass

async def refresh_channels(guild):
	print(guild.id)
	conn = sqlite3.connect("information.db")
	for channel in guild.channels:
		if isinstance(channel, discord.channel.TextChannel) and channel.id not in banned_channels: #TODO: and it's a channel i get to see
			#look up the channel ID in db:
			c = conn.cursor()
			c.execute('SELECT * FROM channels WHERE channel_ID=?', (channel.id,))
			rows = c.fetchall()
			if len(rows) > 0: #it's already there; keep the current color
				c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
				c.execute('INSERT INTO channels VALUES(?,?,?,?)', (guild.id, channel.id, rows[0][2], channel.name))
#				print("skipping", channel.name)
			else:
				c.execute('INSERT INTO channels VALUES(?,?,?,?)', (guild.id, channel.id, "#202020", channel.name))
			conn.commit()
			c.close()
	conn.close()

async def change_channel_color(channel, new_color): #UNTESTED. 
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM channels WHERE channel_ID=?', (channel.id,))
	rows = c.fetchall()
	if len(rows) == 0:
		print("nonexistent channel or i can't access it")
	else:
		c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
		c.execute('INSERT INTO channels VALUES(?,?,?,?)', (channel.guild.id, channel.id, new_color, channel.name))
		print("channel " + channel.name + "'s' color has been updated to " + new_color)
		conn.commit()
		c.close()
	conn.close()


async def add_banned_channel(channel):
	global banned_channels
	if str(channel.id) in banned_channels:
		return False
	f = open('banned_channels.csv', 'a')
	f.write(','+str(channel.id))
	f.close()
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
	c.execute('DELETE FROM messages WHERE channel_ID=?', (channel.id,))
	conn.commit()
	c.close()
	conn.close()
	banned_channels = open('banned_channels.csv').read().split(',')
	return True

def refresh_emoji(guild):
	pass

def refresh_messages(guild):
	pass

def send_query(query):
	pass

async def set_color(message):
	channel = message.channel_mentions[0]
	color = message.content.split()[2]
	await change_channel_color(channel, color)


@client.event
async def on_message(message):
	if "!add_ignored_channel" in message.content and "ezekiel" in str(message.author):
		for channel in message.channel_mentions:
			if not await add_banned_channel(channel): 
				print("sad face")
				await message.add_reaction('❌')
		await message.add_reaction(":eyes1:644066672914726922")
	if "!set_color" in message.content and "ezekiel" in str(message.author):
		#message must be: !set_color [channel] #[color in hex]
		await set_color(message)
		await message.add_reaction(":eyes1:644066672914726922")

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

	for server in client.guilds:
		if "CMU" in str(server):
			await refresh_channels(server)

client.run(token)


#conn = sqlite3.connect("db2.db")
#c = conn.cursor()
#c.execute(''' INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)''', (msg[0], msg[1], msg[2], msg[3], msg[4], msg[5], msg[6], msg[7], msg[8]))
#conn.commit() 
#c.close()
#conn.close()
