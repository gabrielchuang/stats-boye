from enum import Enum
import re
import discord
import sqlite3
import pandas as pd
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import json
from datetime import datetime

class InvalidQuery(Exception):
	pass

class T(Enum):
	CHANNEL = 1
	USER = 2
	KEYWORD = 3
	ROLE = 4
	REACT = 6
	#CUSTOM_REACT = 7
	DATE_RANGE = 8
	IS_PINNED = 9
	HAS_IMAGE = 10
	EXCLUDE_BOTS = 11
	CASE_SENSITIVE = 12
	PINGS = 13
	KEYWORD_INSENSITIVE = 14
	N_CHANNEL = -1
	N_USER = -2
	N_KEYWORD = -3
	N_ROLE = -4

class ShadowUser():
	def __init__(self, id, guild):
		self.id = id
		conn = sqlite3.connect(str(guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT username FROM users WHERE user_ID=?', (self.id,))
		self.name = c.fetchall()[0][0]
	def __eq__(self, other):
		return self.id == other.id
	def __hash__(self):
		return hash(self.id)

'''
usage:
	filtering by channel 		--- 	channel:`general`	#general	[id # of general]
	filtering by user 			--- 	user:`samcv`		@samcv		[id # of samcv]
	filtering by role 			--- 	role:`weeb`			@weeb		[id # of weeb role]
	filtering by keyword 		--- 	keyword:`keyword here`
	filtering by date range 	--- 	date-range:`2020-01-31 12:30:40 -- 2020-05-21`
	filtering by pings 			--- 	pings:`ezekiel` 

	filtering by reactions 		--- 	has-react:📈					(for standard emoji)
						   		--- 	has-custom-react:`eyes1`		(for custom emoji)

	exclude bots from results 	--- 	--exclude-bots (off by default)                                   UNDER CONSTRUCTION
	enabling case-sensitivity 	--- 	--case-sensitive (off by default)
	presence of attachments 	--- 	--no-image 		OR 		--has-image (neither by default)
	pinned 						--- 	--pinned 		OR 		--not-pinned


	split-by:`channel` or split-by:`user`
'''



class Query:

	def __init__(self, message, client):
		#haha parsing go brrr
		self.client = client
		self.message = message

		self.case_sensitive = self.parse_case_sensitive() # bool
		
		self.excludebots = self.parse_exclude_bots() # bool
		self.has_image = self.parse_has_image() # bool OPTION
		self.is_pinned = self.parse_is_pinned() # bool OPTION

		self.daterange = self.parse_daterange()

		#filters : (T enum -> 'a' list) dictionary
		channels, not_channels = self.parse_channels()
		roles, not_roles = self.parse_roles()
		users, not_users = self.parse_users()
		keywords, not_keywords = self.parse_keywords()

		self.filters = {T.CHANNEL : channels,  							# channel object list
						T.N_CHANNEL : not_channels,
						T.USER: users,				 					# user object list
						T.N_USER : not_users,
						T.KEYWORD: keywords, 							# string list
						T.N_KEYWORD : not_keywords,
						T.ROLE: roles,				 					# role object list
						T.N_ROLE: not_roles,
						T.REACT: self.parse_hasreact() + self.parse_hasreact_custom(), 	# string/id list
						T.PINGS : self.parse_pings(), 					# user object list
						T.DATE_RANGE: self.parse_daterange(), 			# string * string tuple option
						T.IS_PINNED: self.parse_is_pinned(),  			# bool option
						T.HAS_IMAGE: self.parse_has_image(),  			# bool option
						T.EXCLUDE_BOTS: self.parse_exclude_bots(),		# bool
						T.CASE_SENSITIVE: self.parse_case_sensitive()} 	# bool

		self.filter_strings = {T.CHANNEL : """ messages.channel_ID = ? """, # channel.id
					  T.USER : """ messages.author_ID = ? """,  # user.id
					  T.KEYWORD : """ messages.content LIKE '%'||?||'%' """, # just the string
					  T.KEYWORD_INSENSITIVE : """ lower(messages.content) LIKE '%'||?||'%' """, # just the string
					  T.ROLE : """ users.roles LIKE '%'||?||'%' """, # role.id
					  T.REACT : """ messages.reacts LIKE '%'||?||'%'  """, #just the string
					  T.PINGS : """ messages.user_pings LIKE '%'||?||'%' """, # user.id
					  T.DATE_RANGE : """ ? < messages.timestamp AND messages.timestamp < ? """, # pass in the two elements of tuple separately!
					  T.IS_PINNED : """ messages.pinned = ? """, # 0 or 1
					  T.HAS_IMAGE : """ messages.has_attachments = ? """, # 0 or 1
					  T.EXCLUDE_BOTS : """ users.privs != 1 """
					  }


	# returns filter string, and args. kindly ignore the extreme inelegance. 
	# sql_filter_string : returns a string consisting of the stuff after 'WHERE' in the sql query. Does not include 'WHERE'
	# 							  and the arguments list that goes with the query. 
	def sql_filter_string(self):
		where = ' '
		args = []
		for filter_type in (T.CHANNEL, T.USER, T.ROLE, T.PINGS):
			if len(self.filters[filter_type]) == 0:
				continue
			where += " AND (" + "OR".join([self.filter_strings[filter_type] for x in self.filters[filter_type]]) + ")"
			args += [x.id for x in self.filters[filter_type]]

		for filter_type in [T.N_CHANNEL, T.N_ROLE, T.N_USER]:
			if len(self.filters[filter_type]) == 0:
				continue
			where += " AND (" + "AND".join([" NOT " + self.filter_strings[T(filter_type.value * -1)] for x in self.filters[filter_type]]) + ")"
			args += [x.id for x in self.filters[filter_type]]

		if len(self.filters[T.KEYWORD]) != 0:
			if self.filters[T.CASE_SENSITIVE]:
				where += " AND (" + "OR".join([self.filter_strings[T.KEYWORD] for x in self.filters[T.KEYWORD]]) + ")"
				args += self.filters[T.KEYWORD]
			else:
				where += " AND (" + "OR".join([self.filter_strings[T.KEYWORD_INSENSITIVE] for x in self.filters[T.KEYWORD]]) + ")"
				args += [x.lower() for x in self.filters[T.KEYWORD]]

		if len(self.filters[T.N_KEYWORD]) != 0:
			if self.filters[T.CASE_SENSITIVE]:
				where += " AND (" + "AND".join([" NOT " + self.filter_strings[T.KEYWORD] for x in self.filters[T.N_KEYWORD]]) + ")"
				args += self.filters[T.N_KEYWORD]
			else:
				where += " AND (" + "AND".join([" NOT " + self.filter_strings[T.KEYWORD_INSENSITIVE] for x in self.filters[T.N_KEYWORD]]) + ")"
				args += [x.lower() for x in self.filters[T.N_KEYWORD]]


		if len(self.filters[T.REACT]) != 0:
			where += " AND (" + "OR".join([self.filter_strings[T.REACT] for x in self.filters[T.REACT]]) + ")"
			args += self.filters[T.REACT]

		if self.filters[T.DATE_RANGE] != None: 
			where += " AND (" + self.filter_strings[T.DATE_RANGE] + ")"
			args += [self.filters[T.DATE_RANGE][0], self.filters[T.DATE_RANGE][1]]

		for filter_type in (T.IS_PINNED, T.HAS_IMAGE):
			if self.filters[filter_type] != None: 
				where += " AND (" + self.filter_strings[filter_type] + ")"
				args.append(1 if self.filters[filter_type] else 0)

		if self.filters[T.EXCLUDE_BOTS]:
			where += " AND " + self.filter_strings[T.EXCLUDE_BOTS]

		print(where)

		return (where, args)			

	# sql_joins_strings : given the rest of the stuff in the query, determines what tables need to be included. 
	#						currently really hacky D:  -- needs to be called after parse_split and sql_filter_string are called,
	# 						and self.filter_str and self.split are assigned. 
	def sql_joins_string(self, otherstuff=""):
		rest = self.filter_str + " " + self.split[1] + " " + otherstuff
		inner_join = ''
		if "channels." in rest:
			inner_join += " INNER JOIN channels ON channels.channel_ID = messages.channel_ID "
		if "users." in rest: 
			inner_join += " INNER JOIN users ON (users.user_ID = messages.author_ID and users.guild_ID = messages.guild_ID) "
		return inner_join 

	def parse_channels(self):
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT name, channel_ID  FROM channels WHERE guild_ID=?', (self.message.guild.id,))
		channel_info =  dict(c.fetchall())

		channels = self.message.channel_mentions

		channel_names =  re.findall('channel:`#?(?P<ch>.*?)`', self.message.content)
		if len(set(channel_names) - set(channel_info.keys())) > 0:
			raise InvalidQuery('invalid channel(s): '+ str(set(channel_names) - set(channel_info.keys())))
		channels += [self.client.get_channel(channel_info[name]) for name in channel_names]
		if None in channels: 
			raise InvalidQuery('invalid channel(s)')

		anti_channel_names =  re.findall('~channel:`#?(?P<ch>.*?)`', self.message.content)
		anti_channels = [self.client.get_channel(channel_info[name]) for name in anti_channel_names]

		channels = list(set(channels) - set(anti_channels))

		channels += [self.client.get_channel(c) for c in filter((lambda x : str(x) in self.message.content), channel_info.values())]

		return list(set(channels)), list(set(anti_channels))

	def parse_roles(self):
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT name, role_ID  FROM roles WHERE guild_ID=?', (self.message.guild.id,))
		role_info = dict(c.fetchall())

		roles = self.message.role_mentions

		role_names =  re.findall('role:`@?(?P<ch>.*?)`', self.message.content)
		if len(set(role_names) - set(role_info.keys())) > 0:
			raise InvalidQuery('invalid role(s): '+ str(set(role_names) - set(role_info.keys())))
		roles += [self.message.guild.get_role(role_info[name]) for name in role_names]
		if None in roles: 
			raise InvalidQuery('invalid role(s)')

		anti_role_names =  re.findall('~role:`@?(?P<ch>.*?)`', self.message.content)
		anti_roles = [self.message.guild.get_role(role_info[name]) for name in anti_role_names]
		roles = list(set(roles) - set(anti_roles))

		roles += [self.message.guild.get_role(c) for c in filter((lambda x : str(x) in self.message.content), role_info.values())]
		return list(set(roles)), list(set(anti_roles))

	def parse_users(self):
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT username, user_ID FROM users WHERE guild_ID=?', (self.message.guild.id,))
		user_info = dict(c.fetchall())

		users = [ShadowUser(x.id, self.message.guild) for x in self.message.mentions]

		user_names = re.findall('user:`@?(?P<ch>.*?)`', self.message.content)
		if len(set(user_names) - set(user_info.keys())) > 0:
			raise InvalidQuery('invalid user(s): '+ str(set(user_names) - set(user_info.keys())))

		users += [ShadowUser(user_info[name], self.message.guild) for name in user_names]

		anti_user_names = re.findall('~user:`@?(?P<ch>.*?)`', self.message.content)
		anti_users = [ShadowUser(user_info[name], self.message.guild) for name in anti_user_names]
		users = list(set(users) - set(anti_users))

		users += [ShadowUser(c, self.message.guild) for c in filter((lambda x : str(x) in self.message.content), user_info.values())]
		return list(set(users)), list(set(anti_users))

	def parse_keywords(self): 
		inits = re.findall('keyword:`(?P<ch>.*?)`', self.message.content)
		anti_inits = re.findall('~keyword:`(?P<ch>.*?)`', self.message.content)
		inits = list(set(inits) - set(anti_inits))

		print(inits)
		print(self.message.content)

		# rip how discord deals with emoji and backtick delimiters D;
		f = open('emoji_map.json')
		d = json.load(f)
		keywords = []
		for keyword in inits: 
			found = False
			for poss in d.keys():
				if ":"+poss+":" in keyword:
					keywords.append(keyword.replace(":"+poss+":", d[poss]))
					found = True
					break
			if not found:
				keywords.append(keyword)
		anti_keywords = []
		for keyword in anti_inits: 
			found = False
			for poss in d.keys():
				if ":"+poss+":" in keyword:
					anti_keywords.append(keyword.replace(":"+poss+":", d[poss]))
					found = True
					break
			if not found:
				anti_keywords.append(keyword)

		return keywords, anti_keywords

	def parse_pings(self):
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT username, user_ID FROM users WHERE guild_ID=?', (self.message.guild.id,))
		user_info = dict(c.fetchall())

		user_names =  re.findall('pings:`@?(?P<ch>.*?)`', self.message.content)
		if len(set(user_names) - set(user_info.keys())) > 0:
			raise InvalidQuery('invalid user ping(s): '+ str(set(user_names) - set(user_info.keys())))
		pings = [self.client.get_user(user_info[name]) for name in user_names]
		if None in pings: 
			raise InvalidQuery('invalid user ping(s)')
		return list(set(pings))
	def parse_daterange(self):
		daterange = re.findall('date-range:`(?P<ch>.*?)`', self.message.content)
		if len(daterange) == 0: return None 
		elif len(daterange) > 1: raise InvalidQuery('multiple date ranges specified')
		else:
			ends = daterange[0].split(' -- ')
			if len(ends) != 2: raise InvalidQuery('must specify two dates for date range')
			if all([re.match('^\d{4}-\d\d-\d\d( \d\d)*(:\d\d)*(:\d\d)*$', x) for x in ends]):
				return (ends[0], ends[1])
			else: raise InvalidQuery('dates are poorly formatted: must be YYYY-MM-DD[ HH:mm:SS], (hours/mins/seconds optional). Example: date-time:`2020-01-01 -- 2020-05-01 23:59:59`')
	def parse_hasreact_custom(self):
		hasreacts = re.findall('has-custom-react:`#?(?P<ch>.*?)`', self.message.content)
		custom_reacts = []
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		for emoji in hasreacts:
			if len(emoji) == 1: 
				pass
			else:
				c = conn.cursor()
				c.execute('SELECT emoji_ID FROM emojis WHERE emoji_name=?', (emoji,))
				x = c.fetchall()
				if len(x) != 1: raise InvalidQuery('emoji not defined. nitro emoji from other servers aren\'t yet supported')
				else: 
					custom_reacts.append(x[0][0])
		conn.close()
		return custom_reacts
	def parse_hasreact(self):
		emojis = re.findall('has-react:(?P<ch>.?)', self.message.content)
		return emojis

	def parse_exclude_bots(self):
		if '--exclude-bots' in self.message.content:
			return True
		return False
	def parse_case_sensitive(self):
		if '--case-sensitive' in self.message.content:
			return True
		return False
	def parse_has_image(self):
		if '--no-image' in self.message.content:
			return False
		elif '--has-image' in self.message.content:
			return True
		else:
			return None
	
	def parse_is_pinned(self):
		if '--pinned' in self.message.content:
			return True
		elif '--not-pinned' in self.message.content:
			return False
		else:
			return None

	def parse_split(self, default=T.USER):
		split =  re.findall('split-by:`(?P<ch>.*?)`', self.message.content)
		if len(split) == 0:
			return default
		d = {'channel' : (T.CHANNEL, 'channels.name', 'channel', 'channels'),
			 'user' : (T.USER, 'users.username', 'user', 'users')}
		try:
			return d[split[0]]
		except KeyError:
			raise InvalidQuery('invalid split-by: ' + str(split[0]))

	def pretty_filter_string(self): 
		s = ''
		for x in self.filters.keys():
			if type(self.filters[x]) == list:
				if len(self.filters[x]) != 0:
					s += str(x) + ": " + ", ".join([str(y) for y in self.filters[x]]) + "\n"
			elif self.filters[x] != None: 
				s += str(x) + ": " + str(self.filters[x]) + "\n"
		return s

	def titler(self):
		if self.filters[T.USER] != []: 
			title = ", ".join([x.name for x in self.filters[T.USER]])
		elif self.filters[T.ROLE] != []:
			title = ", ".join([x.name for x in self.filters[T.ROLE]])
		else:
			title = "messages"

		if self.filters[T.CHANNEL] != []:
			title += " in " + ", ".join(["#"+x.name for x in self.filters[T.CHANNEL]])
		return title

	def get_a_color(self):
		if len(self.filters[T.ROLE]) > 0:
			colors = str(self.filters[T.ROLE][0].color)
		elif len(self.filters[T.USER]) > 0:
			conn = sqlite3.connect(str(self.message.guild.id)+".db")
			c = conn.cursor()
			c.execute(' SELECT color FROM users WHERE user_ID=? and guild_ID=?', (self.filters[T.USER][0].id, self.message.guild.id))
			colors = str(c.fetchall()[0][0])
		elif len(self.filters[T.CHANNEL]) > 0:
			conn = sqlite3.connect(str(self.message.guild.id)+".db")
			c = conn.cursor()
			c.execute(' SELECT color FROM channels WHERE channel_ID=? and guild_ID=?', (self.filters[T.CHANNEL][0].id, self.message.guild.id))
			colors = str(c.fetchall()[0][0])
		else:
			colors = '#304FFE'
		return colors

class About(Query):
	def __init__(self, message, client): 
		super().__init__(message, client)
		cc = open('command_character.txt').read()[0] # command character

		if cc+"aboutme" in message.content:
			if self.filters[T.USER] != []:
				embed=discord.Embed(title="use !about to use more filters. !aboutme is just for you! ", color=0xff0000)
				self.embed = embed
				return
			self.filters[T.USER] = [message.author]

		self.split = (None, '', '', '')
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor() 

		query_secondhalf = ''' FROM messages %s WHERE 1=1 %s ''' % (self.join_str, self.filter_str)

		c.execute(''' SELECT COUNT(*) ''' + query_secondhalf, self.args)
		total_messages = c.fetchall()[0][0]

		c.execute(''' SELECT COUNT(*) ''' + query_secondhalf + " AND length(clean_content) - length(replace(clean_content, ' ', '')) = 0", self.args)
		num_singleword_messages = c.fetchall()[0][0]

		c.execute(''' SELECT COUNT(*) ''' + query_secondhalf + " AND pinned = 1", self.args)
		num_pinned = c.fetchall()[0][0]

		c.execute(''' SELECT COUNT(*) ''' + query_secondhalf + " AND has_attachments = 1", self.args)
		num_images = c.fetchall()[0][0]

		c.execute(''' SELECT timestamp, clean_content ''' + query_secondhalf + " AND clean_content != '' ORDER BY timestamp LIMIT 1", self.args)
		first_msg = c.fetchall()[0]
		days_elapsed = float((datetime.now() - datetime.strptime(first_msg[0][:10], '%Y-%m-%d')).days)

		c.execute(''' SELECT SUM(length(clean_content) - length(replace(clean_content, ' ', '')) + 1) ''' + query_secondhalf, self.args)
		total_words = c.fetchall()[0][0]

		c.execute(''' SELECT GROUP_CONCAT(num_reacts||",") ''' + query_secondhalf, self.args)
		reacts = c.fetchall()[0][0]
		num_reacts = sum([int(x) if x != "" else 0 for x in reacts.split(',')])

		c.execute(''' SELECT clean_content, COUNT(clean_content) AS freq ''' + query_secondhalf + ''' AND CLEAN_CONTENT != "" GROUP BY clean_content ORDER BY freq DESC LIMIT 1 ''', self.args)
		most_common_msg = c.fetchall()[0]

		print(self.filters[T.USER])

		if len(most_common_msg[0]) > 400:
			most_common_msg = (most_common_msg[0][:300] + "...", most_common_msg[1])
		if len(first_msg[1]) > 400:
			first_msg = (first_msg[0], first_msg[1][:300] + "...")

		if len(self.filters[T.USER]) == 1:# and all([self.filters[x] == [] for x in set(self.filters.keys()) - set([T.USER])]):
			whomst = self.filters[T.USER][0].name

			p1 = '''%s has sent %d messages in total. Of these: 
			- %d are pinned (%.2f%%)
			- %d have attachments (%.2f%%)
			- %d are only one word or emoji (%.2f%%)

			Their first message was on %s. Since then, they have sent an average of %.2f messages per day. Their first message was:
			>>> %s

			In total, %s has sent %d words, for an average of %.1f words per message. 

			There have been %d reacts on %s's messages, for an average of %.2f reacts per message.

			Their most common non-empty message (%d instances) is:
			>>> %s
			''' % (whomst, total_messages, num_pinned, num_pinned/total_messages*100.0, num_images, num_images/total_messages*100.0, \
				num_singleword_messages, num_singleword_messages/total_messages*100.0, first_msg[0][:11], total_messages/float(days_elapsed), \
				first_msg[1], whomst, total_words, total_words/total_messages, num_reacts, whomst, num_reacts/float(total_messages), most_common_msg[1], most_common_msg[0])
		else: 
			p1 = '''There are %d messages in total that satisfy the filters. Of these: 
			- %d are pinned (%.2f%%)
			- %d have attachments (%.2f%%)
			- %d are only one word or emoji (%.2f%%)

			The first message was on %s. Since then, there have been an average of %.2f messages per day that satisfy the filters. The first message was:
			> %s

			In total, there have been %d words, for an average of %.1f words per message. 

			There have been %d reacts, for an average of %.2f reacts per message.

			The most common non-empty message (%d instances) is:
			> %s
			''' % (total_messages, num_pinned, num_pinned/total_messages*100.0, num_images, num_images/total_messages*100.0, \
				num_singleword_messages, num_singleword_messages/total_messages*100.0, first_msg[0][:11], total_messages/float(days_elapsed), \
				first_msg[1], total_words, total_words/float(total_messages), num_reacts, num_reacts/float(total_messages), most_common_msg[1], most_common_msg[0])

		print("embed length is " + str(len(p1)))

		embed=discord.Embed(title="About "+self.titler(), color=int(self.get_a_color()[1:], 16))
		embed.add_field(name="-", value=p1, inline=False)
		embed.set_footer(text="requested by "+str(self.message.author))

		self.embed = embed

	async def send(self):
		await self.message.channel.send(embed=self.embed)


class RandomQuote(Query):
	def __init__(self, message, client):
		super().__init__(message, client)

		self.split = self.parse_split(default=(None, '', '', ''))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string(otherstuff="users.username ")

		numquotes = self.parse_numquotes()
		if numquotes == None:
				embed=discord.Embed(title="randomquotes limited to 10 per query.", color=0xff0000)
				self.embed = embed
				return

		query = '''SELECT clean_content, jump_url, users.username, timestamp FROM messages INNER JOIN channels on messages.channel_ID = channels.channel_ID %s WHERE channels.privs != 2 %s ORDER BY RANDOM() LIMIT %d''' % (self.join_str, self.filter_str, numquotes)
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute(query, self.args)
		randomquotes = c.fetchall()

		embed=discord.Embed(title="random quote(s)!", color=0xEC407A)

		print(numquotes)
		print(randomquotes)

		for quote in randomquotes:
			text = quote[0]
			jump_url = quote[1]
			name = quote[2]
			date = quote[3]

			embed.add_field(name=name, value=">>> " + text, inline=False)
			embed.add_field(name=date, value=jump_url, inline=False)
		embed.set_footer(text="requested by "+str(self.message.author))

		self.embed = embed

	def parse_numquotes(self):
		numquotes = re.findall('num:?`(\d+)?`', self.message.content)
		if len(numquotes) == 0:
			return 1
		elif int(numquotes[0]) > 10:
			return None
		return int(numquotes[0])

	async def send(self):
		await self.message.channel.send(embed=self.embed)




