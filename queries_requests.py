from enum import Enum
import re
import discord
import sqlite3

class InvalidQuery(Exception):
	pass

class T(Enum):
	CHANNEL = 1
	USER = 2
	KEYWORD = 3
	ROLE = 4
	DATERANGE = 5
	REACT = 6
	CUSTOM_REACT = 7


'''
usage:
	filtering by channel 		--- 	channel:`general`	#general	[id # of general]
	filtering by user 			--- 	user:`samcv`		@samcv		[id # of samcv]
	filtering by role 			--- 	role:`weeb`			@weeb		[id # of weeb role]
	filtering by keyword 		--- 	keyword:`keyword here`
	filtering by date range 	--- 	date-range:`2020-01-31 12:30:40,2020-05-21`

	filtering by reactions 		--- 	has-react:📈					(for standard emoji)
						   		--- 	has-custom-react:`eyes1`		(for custom emoji)

	exclude bots from results 	--- 	--exclude-bots (off by default)
	enabling case-sensitivity 	--- 	--case-sensitive (off by default)
	presence of attachments 	--- 	--no-image 		OR 		--has-image (neither by default)
	pinned 						--- 	--pinned 		OR 		--not-pinned
'''

class Query:

	def __init__(self, message, client):
		#haha parsing go brrr
		self.client = client

		self.message = message
		
		self.excludebots = self.parse_exclude_bots() # bool
		self.case_sensitive = self.parse_case_sensitive() # bool
		self.has_image = self.parse_has_image() # bool OPTION
		self.is_pinned = self.parse_is_pinned() # bool OPTION

		#filters : (T enum -> 'a' list) dictionary
		self.filters = {T.CHANNEL : self.parse_channels(),  #channel object list
						T.USER: self.parse_users(), # user object list
						T.KEYWORD: self.parse_keywords(), #string list
						T.ROLE: self.parse_roles(), # role object list
						T.DATERANGE: self.parse_daterange(),  #string * string
						T.REACT: self.parse_hasreact(),  #string list
						T.CUSTOM_REACT: self.parse_hasreact_custom()} #id list

	def construct_sql_query(self):
		pass

	def parse_channels(self):
		conn = sqlite3.connect("information.db")
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
		conn = sqlite3.connect("information.db")
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
		conn = sqlite3.connect("information.db")
		c = conn.cursor()
		c.execute('SELECT username, user_ID FROM users WHERE guild_ID=?', (self.message.guild.id,))
		user_info = dict(c.fetchall())

		users = self.message.mentions

		user_names =  re.findall('user:`@?(?P<ch>.*?)`', self.message.content)
		if len(set(user_names) - set(user_info.keys())) > 0:
			raise InvalidQuery('invalid user(s): '+ str(set(user_names) - set(user_info.keys())))
		users += [self.client.get_user(user_info[name]) for name in user_names]
		if None in users: 
			raise InvalidQuery('invalid user(s)')

		users += [self.client.get_user(c) for c in filter((lambda x : str(x) in self.message.content), user_info.values())]
		return list(set(users))
	def parse_keywords(self): 
		keywords = re.findall('keyword:`(?P<ch>.*?)`', self.message.content)
		return keywords

	def parse_daterange(self):
		daterange = re.findall('date-range:`(?P<ch>.*?)`', self.message.content)
		if len(daterange) == 0: return None 
		elif len(daterange) > 1: raise InvalidQuery('multiple date ranges specified')
		else:
			ends = daterange[0].split(',')
			if len(ends) != 2: raise InvalidQuery('must specify two dates for date range')
			if all([re.match('^\d{4}-\d\d-\d\d( \d\d)*(:\d\d)*(:\d\d)*$', x) for x in ends]):
				return (ends[0], ends[1])
			else: raise InvalidQuery('dates are poorly formatted: must be YYYY-MM-DD[ HH:mm:SS], (hours/mins/seconds optional). Example: date-time:`2020-01-01,2020-05-01 23:59:59`')

	def parse_hasreact_custom(self):
		hasreacts = re.findall('has-custom-react:`#?(?P<ch>.*?)`', self.message.content)
		custom_reacts = []
		for emoji in hasreacts:
			if len(emoji) == 1: 
				pass
			else:
				conn = sqlite3.connect('information.db')
				c = conn.cursor()
				c.execute('SELECT emoji_ID FROM emojis WHERE emoji_name=?', (emoji,))
				x = c.fetchall()
				if len(x) != 1: raise InvalidQuery('emoji not defined; please run !add_emoji [emoji] if it\'s a custom/nitro emote from a different server')
				else: 
					custom_reacts.append(x[0][0])
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

class PieChart(Query):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "pie"
		self.num_slices = 10

class TimeChart(Query):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "time"
		self.time_interval = 1

class BarChart(Query):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "bar"
		self.num_bars = 10
		self.proportion = False



'''

!pie : slices are people, channels
!time : slices are people, keyword, channel, role

!bar : slices are people


'''