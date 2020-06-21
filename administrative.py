import discord
import sqlite3
import datetime
import re
import random
from queries import *

cc = open('command_character.txt').read()[0]

banned_channels = open('banned_channels.csv').read().split(',')
auth_admins = open('admins.csv').read().strip().split(',')


# refresh_users : clears out the users table for the given guild and rebuilds it from scratch. 
# 	returns True
async def refresh_users(guild): 
	conn = sqlite3.connect("information.db")
	mems = []
	c = conn.cursor()
	for member in guild.members:
		c.execute('SELECT privs, color FROM users WHERE user_ID=? and guild_ID=?', (member.id, guild.id))
		try:
			privs, color = c.fetchall()[0]
			print(color)
			if color == None:
				color = "#%06x" % random.randint(0, 0xFFFFFF)

		except IndexError:
			privs = 0
			color = "#%06x" % random.randint(0, 0xFFFFFF)
		mems.append((member.id, member.name, ",".join([str(x.id) for x in member.roles]), guild.id, privs, color))
	c.execute('DELETE FROM users WHERE guild_ID=? and privs <> -1', (guild.id,))
	c.executemany('INSERT INTO users VALUES(?,?,?,?,?,?)', mems)
	conn.commit()
	c.close()
	conn.close()
	return True


# refresh_roles : clears out the roles table for the given guild and rebuilds it from scratch. 
# 	returns True
async def refresh_roles(guild):
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM roles WHERE guild_ID=?', (guild.id,))
	conn.commit()
	c.close()

	roles = []
	for role in guild.roles:
		roles.append((role.id, guild.id, role.name, str(role.color)))
	c = conn.cursor()
	c.executemany('INSERT INTO roles VALUES(?,?,?,?)', roles)
	conn.commit()
	c.close()
	conn.close()
	return True

# refresh_emoji : clears out the roles table for the given guild and rebuilds it from scratch. 
# 	returns True
async def refresh_emojis(guild):
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM emojis WHERE guild_ID=?', (guild.id,))
	conn.commit()
	c.close()

	emojis = []
	for emoji in guild.emojis:
		emojis.append((emoji.id, guild.id, emoji.name, str(emoji.url)))
	c = conn.cursor()
	c.executemany('INSERT INTO emojis VALUES(?,?,?,?)', emojis)
	conn.commit()
	c.close()
	conn.close()
	return True

# refresh_channels : goes through all channels of guild and updates their names, adds any 
# 		new channels, etc. preserves color of existing channels. 
#	returns True
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
				color = "#%06x" % random.randint(0, 0xFFFFFF)
				c.execute('INSERT INTO channels VALUES(?,?,?,?)', (guild.id, channel.id, color, channel.name))
			conn.commit()
			c.close()
	conn.close()
	return True

# change_channel_color : changes the color associated with a given channel in the db. 
async def change_channel_color(channel, color): 
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM channels WHERE channel_ID=?', (channel.id,))
	rows = c.fetchall()
	if len(rows) == 0:
		print("nonexistent channel or i can't access it")
		return False 
	else:
		c.execute('DELETE FROM channels WHERE channel_ID=?', (channel.id,))
		c.execute('INSERT INTO channels VALUES(?,?,?,?)', (channel.guild.id, channel.id, color, channel.name))
		print("channel " + channel.name + "'s color has been updated to " + color)
		conn.commit()
		c.close()
	conn.close()
	return True

# change_user_color : changes the color associated with a given user in the db. 
async def change_user_color(user, color, guild): 
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM users WHERE user_ID=? and guild_ID=?', (user.id, guild.id))
	rows = c.fetchall()
	print(rows[0])
	if len(rows) == 0:
		print("nonexistent user or i can't access it")
		return False 
	else:
		c.execute('DELETE FROM users WHERE user_ID=? and guild_ID=?', (user.id, guild.id))
		conn.commit()
		c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)', (rows[0][0], rows[0][1], rows[0][2], rows[0][3], rows[0][4], color))
		print("user " + user.name + "'s color has been updated to " + color)
		conn.commit()
		c.close()
	conn.close()
	return True

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


# privileges are represented in the following way: 
# 	0 = standard
# 	1 = bot
# 	2 = admin
async def change_priv(member, new_priv):
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM users WHERE user_ID=? AND guild_ID=?', (member.id, member.guild.id))
	c.execute('INSERT INTO users VALUES (?,?,?,?,?)', (member.id, member.name, ",".join([str(x.id) for x in member.roles]), member.guild.id, new_priv))
	conn.commit()
	c.close()
	conn.close()
	return True 

async def add_admin(user):
	global auth_admins
	if str(user.id) in auth_admins:
		return False
	f = open('admins.csv', 'a')
	f.write(','+str(user.id))
	f.close()
	auth_admins = open('admins.csv').read().split(',')
	return True

# clear_all_entries : deletes all entries in `messages`. returns True. 
async def clear_all_entries():
	return 
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('DELETE FROM messages WHERE 1=1')
	conn.commit()
	c.close()
	conn.close()
	return True

# get_most_recently_added : gets the most recent message in the channel. 
async def get_most_recently_added(channel):
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute('SELECT * FROM messages WHERE channel_ID=? ORDER BY timestamp DESC limit 1', (channel.id,))
	rows = c.fetchall()
	last_id = 0 if len(rows) == 0 else int(rows[0][0])
	c.close()
	conn.close()
	return last_id

# refresh_messages : adds all new messages from the channel to the db. returns num msgs added.
async def refresh_messages(channel):
	last_message_here = await get_most_recently_added(channel)
	
	if channel.id in banned_channels: 
		return False
	conn = sqlite3.connect("information.db")
	message_data = []
	count = 0
	async for message in channel.history(limit=400000):
		#if count % 100 == 0:
		#	print(count)
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

# refresh_all_messages : calls refresh_messages on each channel. 
#	returns False if any fail, else True. 
async def refresh_all_messages(guild): 
	total_messages = 0
	all_success = True
	for channel in guild.channels:
		if isinstance(channel, discord.channel.TextChannel) and str(channel.id) not in banned_channels:
			try: 
				total_messages = total_messages + await refresh_messages(channel)
			except discord.errors.Forbidden:
				print("exception raised on channel", channel.name)
				all_success = False
	print(total_messages, "messages added")
	return all_success

async def sudo(message):
	query = re.findall('```(?P<ch>.*?)```', message.content)
	print(query)
	print(message.content)
	conn = sqlite3.connect("information.db")
	c = conn.cursor()
	c.execute(query[0])

	f = str(c.fetchall())
	print(f)

	await message.channel.send(f[:1900] + "[...]")

	conn.commit()
	c.close()
	conn.close()
	return True

async def add_bot_channels(channel):
	bcs = open('bot-channels.csv')
	bcs2 = bcs.read().split(',')
	if str(channel.id) in bcs:
		return False
	bcs.close()
	f = open('bot-channels.csv', 'a')
	f.write(','+str(channel.id))
	f.close()
	return True

async def run_admin_command(message, client):
	await message.add_reaction('⚙️')
	q = Query(message, client)
	channels = q.filters[T.CHANNEL]
	users = q.filters[T.USER]

	if cc+"add_ignored_channel" in message.content:
		success = all([await add_banned_channel(x) for x in channels]) and len(channels) > 0
	elif cc+"refresh_channels" in message.content:
		success = await refresh_channels(message.guild)
	elif cc+"set_color" in message.content: 
		color = re.search('#[0-9a-fA-F]{6}', message.clean_content).group(0)
		success = all([await change_channel_color(x, color) for x in channels]) and len(channels) + len(users) > 0 \
					and all([await change_user_color(x, color, message.guild) for x in users])
	elif cc+"refresh_users" in message.content:
		success = await refresh_users(message.guild)
	elif cc+"refresh_channel" in message.content:
		success = all([await refresh_messages(x) >= 0 for x in channels]) and len(channels) > 0
	elif cc+"refresh_messages" in message.content:
		success = await refresh_all_messages(message.guild)
	elif cc+"refresh_roles" in message.content:
		success = await refresh_roles(message.guild)
	elif cc+"refresh_emojis" in message.content:
		success = await refresh_emojis(message.guild)
	elif cc+"add_bot" in message.content:
		success = all([await change_priv(message.guild.get_member(x.id), 1) for x in message.mentions]) 
	elif cc+"remove_bot" in message.content:
		success = all([await change_priv(message.guild.get_member(x.id), 0) for x in message.mentions]) 
	elif cc+"sudo" in message.content:
		success = await sudo(message)
	elif cc+"add_bot_channel" in message.content:
		success = all([await add_bot_channel(channel) for channel in channels])
	#elif cc+"add_admin" in message.content:
	#	success = all([await change_priv(message.guild.get_member(x.id), 2) for x in message.mentions]) 
	#elif cc+"remove_admin" in message.content:
	#	success = all([await change_priv(message.guild.get_member(x.id), 0) for x in message.mentions]) 
	else:
		success = False

	await message.remove_reaction('⚙️', message.guild.me)

	if success:
		await message.add_reaction("📈")
	else: 
		await message.add_reaction("❌")
	return success 

