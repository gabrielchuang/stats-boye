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


async def refresh_users(guild): 
	conn = sqlite3.connect("information.db")
	for member in guild.members:
		c = conn.cursor()
		c.execute('INSERT INTO users VALUES(?,?,?)', (member.id, member.name, ",".join([str(x.id) for x in member.roles])))
		conn.commit()
		c.close()
	conn.close()

# refresh_channels : goes through all channels of guild and updates their names, adds any 
# 		new channels, etc. preserves color of existing channels. 
#	returns nothing
async def refresh_channels(guild):
	conn = sqlite3.connect("information.db")
	for channel in guild.channels:
		if isinstance(channel, discord.channel.TextChannel) and channel.id not in banned_channels:
			#look up the channel ID in db:
			c = conn.cursor()
			c.execute('SELECT * FROM channels WHERE channel_ID=?', (channel.id,))
			rows = c.fetchall()
			if len(rows) > 0: #it's already there; keep the current color
				c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
				c.execute('INSERT INTO channels VALUES(?,?,?,?)', (guild.id, channel.id, rows[0][2], channel.name))
			else:
				c.execute('INSERT INTO channels VALUES(?,?,?,?)', (guild.id, channel.id, "#202020", channel.name))
			conn.commit()
			c.close()
	conn.close()

# change_channel_color : changes the color associated with a given channel in the db. 
async def change_channel_color(channel, new_color): 
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM channels WHERE channel_ID=?', (channel.id,))
	rows = c.fetchall()
	if len(rows) == 0:
		print("nonexistent channel or i can't access it")
	else:
		c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
		c.execute('INSERT INTO channels VALUES(?,?,?,?)', (channel.guild.id, channel.id, new_color, channel.name))
		print("channel " + channel.name + "'s color has been updated to " + new_color)
		conn.commit()
		c.close()
	conn.close()

# add_banned_channel : adds a channel to the blacklist (stats bot will treat it like it 
# 		does not exist). Deletes all records associated with the channel. 
# 	returns True if succeeds; False if channel is already banned.
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

async def clear_all_entries():
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM messages WHERE 1=1')
	conn.commit()
	c.close()
	conn.close()

async def get_most_recently_added(channel):
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM messages WHERE channel_ID=? ORDER BY timestamp DESC limit 1', (channel.id,))
	rows = c.fetchall()
	last_id = 0 if len(rows) == 0 else int(rows[0][0])
	c.close()
	conn.close()
	return last_id


async def refresh_messages(channel):
	last_message_here = await get_most_recently_added(channel)
	
	if channel.id in banned_channels: 
		return False
	conn = sqlite3.connect("information.db")
	message_data = []
	count = 0
	async for message in channel.history(limit=400000):
		if count % 100 == 0:
			print(count)
		if message.id == last_message_here:
			break 

		count = count + 1

		timestamp = message.created_at.isoformat(sep=' ', timespec='seconds')
		mentions = ",".join([str(x.id) for x in message.mentions])
		role_mentions = ",".join([str(x.id) for x in message.role_mentions])
		reacts = ",".join([x.emoji if isinstance(x.emoji, str) else str(x.emoji.id) for x in message.reactions])
		num_reacts = ",".join([str(x.count) for x in message.reactions])
		channel_mentions = ",".join([str(x.id) for x in message.channel_mentions])
		has_attachments = 1 if len(message.attachments) > 0 else 0
		is_pinned = 1 if message.pinned else 0

		message_data.append((message.id, message.guild.id, message.author.id, message.channel.id, \
				timestamp, message.content, \
				message.clean_content, message.jump_url, is_pinned, has_attachments, reacts, \
				num_reacts, mentions, role_mentions, channel_mentions))

	c = conn.cursor()
	c.executemany('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', message_data)
	conn.commit()
	c.close()
	conn.close()
	print("added", count, "messages to db from channel", channel.name)
	return count

async def refresh_all_messages(guild): 
	total_messages = 0
	for channel in guild.channels:
		if isinstance(channel, discord.channel.TextChannel) and str(channel.id) not in banned_channels:
			try: 
				total_messages = total_messages + await refresh_messages(channel)
			except discord.errors.Forbidden:
				print("exception raised on channel", channel.name)
	print(total_messages, "messages added")

def send_query(query):
	pass

async def set_color(message):
	channel = message.channel_mentions[0]
	color = message.content.split()[2]
	await change_channel_color(channel, color)

@client.event
async def on_message(message): #currently very basic, just for testing (for now)
	if "!add_ignored_channel" in message.content and "ezekiel" in str(message.author):
		#add_ignored_channel [channel_1] [channel_2] 
		for channel in message.channel_mentions:
			if not await add_banned_channel(channel): 
				await message.add_reaction('❌')
		await message.add_reaction("📈")
	if "!set_color" in message.content and "ezekiel" in str(message.author):
		#message must be: !set_color [channel] #[color in hex]
		await set_color(message)
		await message.add_reaction("📈")
	if "!refresh_users" in message.content and "ezekiel" in str(message.author):
		await refresh_users(message.guild)
		await message.add_reaction("📈")
	if "!refresh_channel" in message.content and "ezekiel" in str(message.author):
		await refresh_messages(message.channel_mentions[0])
		await message.add_reaction("📈")
	if "!clear_messages_table" in message.content and "ezekiel" in str(message.author):
		await clear_all_entries()
		await message.add_reaction("📈")
	if "!refresh_messages" in message.content and "ezekiel" in str(message.author): 
		await refresh_all_messages(message.guild)
		await message.add_reaction("📈")


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

	for server in client.guilds:
		if "CMU" in str(server):
			await refresh_channels(server)

client.run(token)
