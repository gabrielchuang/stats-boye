from enum import Enum
import re
import discord
import sqlite3
import pandas as pd
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import json
import os

from queries import *

class Chart(Query):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.filename = str(message.id)+".png"
		self.verbose = '--verbose' in message.content

	def create_embed(self):
		if self.verbose:
			embed=discord.Embed(title=self.type + " chart", description=self.message.clean_content, color=0x288D1)
			embed.add_field(name="SQL query", value=self.query, inline=False)
		else:
			embed = discord.Embed(color=0xff00ff)
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
		print(self.split)

		self.filter_str, self.args = self.sql_filter_string()
		self.join_str = self.sql_joins_string()

		self.query = self.construct_sql_query()

	def parse_slices(self):
		slices =  re.findall('slices:`?(?P<ch>[0-9]*)`?', self.message.content)
		if len(slices) == 0:
			return 10
		print(slices)
		return int(slices[0])


	def construct_sql_query(self):
		query = ''' SELECT count(messages.ID) as msgs, %s as %s, %s.color FROM messages %s
					WHERE 1=1 %s GROUP BY %s''' % (self.split[1], self.split[2], self.split[3], self.join_str, self.filter_str, self.split[1])
		return query

	def construct_piechart(self): 
		plt.close('all')
		conn = sqlite3.connect("information.db")
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
		self.time_interval = 1

class BarChart(Chart):
	def __init__(self, message, client):
		super().__init__(message, client)
		self.type = "bar"
		self.num_bars = 10
		self.proportion = False
