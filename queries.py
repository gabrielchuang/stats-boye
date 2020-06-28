from enum import Enum
import re
import discord
import sqlite3
import pandas as pd
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import json

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
		self.filters = {T.CHANNEL : self.parse_channels(),  			# channel object list
						T.USER: self.parse_users(), 					# user object list
						T.KEYWORD: self.parse_keywords(), 				# string list
						T.ROLE: self.parse_roles(), 					# role object list
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
		where = ' AND messages.guild_ID = ?'
		args = [self.message.guild.id]
		for filter_type in (T.CHANNEL, T.USER, T.ROLE, T.PINGS):
			if len(self.filters[filter_type]) == 0:
				continue
			where += " AND (" + "OR".join([self.filter_strings[filter_type] for x in self.filters[filter_type]]) + ")"
			args += [x.id for x in self.filters[filter_type]]

		if len(self.filters[T.KEYWORD]) != 0:
			if self.filters[T.CASE_SENSITIVE]:
				where += " AND (" + "OR".join([self.filter_strings[T.KEYWORD] for x in self.filters[T.KEYWORD]]) + ")"
				args += self.filters[T.KEYWORD]
			else:
				where += " AND (" + "OR".join([self.filter_strings[T.KEYWORD_INSENSITIVE] for x in self.filters[T.KEYWORD]]) + ")"
				args += [x.lower() for x in self.filters[T.KEYWORD]]

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

		channels += [self.client.get_channel(c) for c in filter((lambda x : str(x) in self.message.content), channel_info.values())]
		return list(set(channels))

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

		roles += [self.message.guild.get_role(c) for c in filter((lambda x : str(x) in self.message.content), role_info.values())]
		return list(set(roles))
	def parse_users(self):
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute('SELECT username, user_ID FROM users WHERE guild_ID=?', (self.message.guild.id,))
		user_info = dict(c.fetchall())

		users = [ShadowUser(x.id, self.message.guild) for x in self.message.mentions]

		user_names =  re.findall('user:`@?(?P<ch>.*?)`', self.message.content)
		if len(set(user_names) - set(user_info.keys())) > 0:
			raise InvalidQuery('invalid user(s): '+ str(set(user_names) - set(user_info.keys())))

		users += [ShadowUser(user_info[name], self.message.guild) for name in user_names]
#		if None in users: 
#			raise InvalidQuery('invalid user(s)')
		users += [ShadowUser(c, self.message.guild) for c in filter((lambda x : str(x) in self.message.content), user_info.values())]
		return list(set(users))

	def parse_keywords(self): 
		inits = re.findall('keyword:`(?P<ch>.*?)`', self.message.content)
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
		return keywords

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

class AboutMe(Query):
	def __init__(self, message, client): 
		super().init(message, client)

		if len(self.filters[T.USER]) == 0:
			self.filters[T.USER] = [message.author]

		'''
		total messages
		avg messages per day
		first message on server (day)
		avg words per message
		# pinned
		# with images
		# total reacts
		'''

class RandomQuote(Query):
	def __init__(self, message, client):
		super().__init__(message, client)

		self.split = self.parse_split(default=(None, '', '', ''))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string(otherstuff="users.username ")

		query = '''SELECT clean_content, jump_url, users.username, timestamp FROM messages %s WHERE 1=1 %s ORDER BY RANDOM() LIMIT 1''' % (self.join_str, self.filter_str)
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute(query, self.args)
		randomquote = c.fetchall()

		quote = randomquote[0][0]
		jump_url = randomquote[0][1]
		name = randomquote[0][2]
		date = randomquote[0][3]

		embed=discord.Embed(title="random quote!", color=0xEC407A)
		embed.add_field(name=name, value=" > " + quote, inline=False)
		embed.add_field(name=date, value=jump_url, inline=False)
		embed.set_footer(text="requested by "+str(self.message.author))

		self.embed = embed

	async def send(self):
		await self.message.channel.send(embed=self.embed)




