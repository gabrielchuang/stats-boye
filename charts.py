from enum import Enum
import re
import discord
import sqlite3
import pandas as pd
import numpy as np
from matplotlib.colors import ListedColormap
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import json
import os
from datetime import datetime, timedelta
from wordcloud import WordCloud

from queries import *

class Chart(Query):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.filename = str(message.id)+".png"
		self.verbose = '--verbose' in message.content

	def create_embed(self):
		if self.verbose:
			embed=discord.Embed(title=self.type + " chart", description=self.message.clean_content, color=0x304FFE)
			embed.add_field(name="filters", value=self.pretty_filter_string(), inline=False)
			embed.add_field(name="SQL query", value=self.query, inline=False)
			embed.add_field(name="SQL args", value=str(self.args), inline=False)
		else:
			embed = discord.Embed(color=0x304FFE)
		embed.set_footer(text="requested by "+str(self.message.author))
		file = discord.File(self.filename, filename=self.filename)
		embed.set_image(url="attachment://"+self.filename)
		self.embed = embed
		self.file = file

	async def send(self):
		await self.message.channel.send(file=self.file, embed=self.embed)
		os.remove(self.filename)

class PieChart(Chart):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "pie"
		self.num_slices = self.parse_slices()

		self.split = self.parse_split(default=(T.CHANNEL, 'channels.name', 'channel', 'channels'))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()


		self.query = self.construct_sql_query()

	def parse_slices(self):
		slices =  re.findall('slices:`?(?P<ch>[0-9]*)`?', self.message.content)
		if len(slices) == 0:
			return 15
		print(slices)
		return int(slices[0])

	def construct_sql_query(self):
		query = ''' SELECT count(messages.ID) as msgs, %s as %s, %s.color FROM messages %s
					WHERE 1=1 %s GROUP BY %s''' % (self.split[1], self.split[2], self.split[3], self.join_str, self.filter_str, self.split[1])
		return query

	def construct_piechart(self): 
		plt.close('all')
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		df = pd.read_sql_query(self.query, conn, params=self.args)
		df = df.sort_values(by='msgs', ascending=False)

		if len(df) > self.num_slices:
			print('hi')
			minslicesize = (df.iloc[self.num_slices]['msgs'])
			other_qty = df.loc[df['msgs'] <= minslicesize,['msgs']].sum(axis=0)['msgs']
			print(df)
			df.loc[len(df)] = [other_qty, 'other', '#F5F5F5']
			print(other_qty)
			print(df)
			df = df[df['msgs'] > minslicesize]	

		df = df.set_index(self.split[2])
		ax = plt.subplot(111, aspect='equal')
		ax.set_ylabel('')

		print(df)

		df.plot(kind='pie', y='msgs', ax=ax, legend=False, startangle=90, \
			counterclock=False, autopct='%1.0f%%', pctdistance=0.8, colors=df['color'].tolist())

		plt.gca().axes.get_yaxis().set_visible(False)
		plt.tight_layout()
		plt.savefig(self.filename)
		conn.close()

class TimeChart(Chart):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "time"

		if 'interval:`minute`' in self.message.content:
			self.interval = 'minute'
		else:
			self.interval = 'date'


		self.split = self.parse_split(default=(None,"","",""))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		self.query = self.construct_sql_query()


	def construct_sql_query(self):
		if self.interval == 'date':
			timestamp_string = "substr(messages.timestamp, 1, 10)"
		elif self.interval == 'minute':
			timestamp_string = "substr(messages.timestamp, 12, 5)"

		if self.split[0] == None:
			query = ''' SELECT count(messages.ID) as msgs, %s as timestamp FROM messages %s
					WHERE 1=1 %s GROUP BY %s''' % (timestamp_string, self.join_str, self.filter_str, timestamp_string)
		else:
			query = ''' SELECT count(messages.ID) as msgs, %s as %s, %s.color as color, %s as timestamp FROM messages %s
					WHERE 1=1 %s GROUP BY %s, %s''' % (self.split[1], self.split[2], self.split[3], timestamp_string, self.join_str, self.filter_str, timestamp_string, self.split[1])
		return query

	def construct_timechart(self):
		plt.close('all')

		print(self.query)

		conn = sqlite3.connect(str(self.message.guild.id)+".db")

		ax = plt.subplot(111)
		ax.set_ylabel('msgs')

		if self.interval == 'date':
			df = pd.read_sql_query(self.query, conn, params=self.args, parse_dates='timestamp')

			if self.split[0] == None:
				df.plot(kind='line', ax=ax, x='timestamp', y='msgs', color=self.get_a_color())
			else:
				for x in self.filters[self.split[0]]:
					df0 = df[df[self.split[2]] == x.name]
					df0.plot(kind='line', ax=ax, color=df0['color'], x='timestamp', y='msgs', label=str(x.name))

		elif self.interval == 'minute': 
			df = pd.read_sql_query(self.query, conn, params=self.args)

			if self.split[0] == None:
				g = [datetime.strptime(ts, '%H:%M') + timedelta(hours=-4) for ts in df['timestamp']]
				matplotlib.pyplot.plot_date(matplotlib.dates.date2num(g), df['msgs'], ls='solid', marker=None, color=self.get_a_color())

			else:
				for x in self.filters[self.split[0]]:
					df0 = df[df[self.split[2]] == x.name]
					print(df0)
					g = [datetime.strptime(ts, '%H:%M') + timedelta(hours=-4) for ts in df0['timestamp']]
					dates = matplotlib.dates.date2num(g)
					matplotlib.pyplot.plot_date(dates, df0['msgs'], ls='solid', marker=None, color=list(df0['color'])[0], label=str(x.name))
			plt.legend()
			plt.gca().xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

		plt.tight_layout()
		plt.savefig(self.filename)
		conn.close()

class BarChart(Chart):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "bar"
		self.num_bars = self.parse_bars()

		self.split = self.parse_split(default=(T.USER, 'users.username', 'user', 'users'))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		self.query = self.construct_sql_query()

	def parse_bars(self):
		bars =  re.findall('bars:`?(?P<ch>[0-9]*)`?', self.message.content)
		if len(bars) == 0:
			return 10
		print(bars)
		return int(bars[0])

	def construct_sql_query(self):
		query = ''' SELECT count(messages.ID) as msgs, %s as %s, %s.color FROM messages %s
					WHERE 1=1 %s GROUP BY %s ORDER BY count(messages.ID) DESC LIMIT %s''' % (self.split[1], self.split[2], self.split[3], self.join_str, self.filter_str, self.split[1], self.num_bars)
		return query

	def construct_barchart(self): 
		plt.close('all')
		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		
		print(self.query)
		print(self.args)

		df = pd.read_sql_query(self.query, conn, params=self.args)

		df = df.sort_values(by='msgs', ascending=False)


		ax = plt.subplot(111, aspect='equal')
		ax.set_ylabel('msgs')

		print(df)

		colors = [self.get_a_color()]

		df.plot(kind='bar', x=self.split[2], color=colors)
		plt.tight_layout()
		plt.savefig(self.filename)
		conn.close()

class WordCountDistribution(Chart):
	def __init__(self, message, client):

		super().__init__(message, client)

		self.split = self.parse_split(default=(T.USER, 'users.username', 'user', 'users'))
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		self.type = "word count distribution"

		self.query = ''' SELECT  1+length(clean_content) - length(replace(clean_content, ' ', '')) as words, count(ID) as msgs from messages  %s where 1=1 %s 
					GROUP BY length(clean_content) - length(replace(clean_content, ' ', ''))
		'''  % (self.join_str, self.filter_str)

	def construct_wordCountDistributionChart(self):
		plt.close('all')


		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		df = pd.read_sql_query(self.query, conn, params=self.args)
		df = df.sort_values(by='words')

		print(df)

		df['msgs'] = df['msgs']/float(df['msgs'].sum())

		df = df.set_index('words')
		df.plot(kind='line', xlim=(0, 20), logy=('--log' in self.message.content))

		plt.tight_layout()
		plt.savefig(self.filename)
		conn.close()

class MessageCloud(Chart):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "wordcloud"

		self.split = (None, '', '', '')
		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		self.query = '''SELECT group_concat(" "||content||" ") from messages %s WHERE 1=1 %s ''' % (self.join_str, self.filter_str)

		conn = sqlite3.connect(str(self.message.guild.id)+".db")
		c = conn.cursor()
		c.execute(self.query, self.args)
		words = c.fetchall()[0][0]

		wc = WordCloud().generate(words)
		wc.to_file(self.filename)


















