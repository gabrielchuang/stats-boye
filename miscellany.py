import discord
import sqlite3
import re
from queries import *
from administrative import *

async def run_misc_command(message, client):
	await message.add_reaction('⚙️')
	
	cc = open('command_character.txt').read()[0]# command character


	if cc+"set_my_color" in message.content:
		color = re.search('#[0-9a-fA-F]{6}', message.clean_content).group(0)
		success = await change_user_color(message.author, color, message.guild)
	elif any([cc+x in message.content for x in ['basics', 'filters', 'admin', 'misc', 'cheatsheet', 'cs', 'help', 'statshelp']]): 
		success = await send_help(message)
	else:
		success = False

	await message.remove_reaction('⚙️', message.guild.me)
	if success:
		await message.add_reaction("📈")
	else: 
		await message.add_reaction("❌")


async def send_help(message):
	text = open('helptext.txt').read().split('----------')

	if cc+'basics' in message.content:
		embed=discord.Embed(title="How to use stats boye - basics", color=0x288D1)
		embed.add_field(name="basic basics", value=text[0], inline=False)
		embed.add_field(name="split-by", value=text[1], inline=False)
		embed.add_field(name="misc", value=text[2], inline=False)
		embed.add_field(name="for the rest of the helptext, ", value=text[-1], inline=False)
		await message.channel.send(embed=embed)
	elif cc+'filters' in message.content:
		embed=discord.Embed(title="How to use stats boye - filters", color=0x288D1)
		embed.add_field(name="about", value=text[3], inline=False)
		embed.add_field(name="channel", value=text[4], inline=False)
		embed.add_field(name="user", value=text[5], inline=False)
		embed.add_field(name="role", value=text[6], inline=False)
		embed.add_field(name="keyword (just checks substrings, case-insensitive)", value=text[7], inline=False)
		embed.add_field(name="date range", value=text[8], inline=False)
		embed.add_field(name="messages that ping the specified user", value=text[9], inline=False)
		embed.add_field(name=" messages that have been reacted to with the specified emoji", value=text[10], inline=False)
		embed.add_field(name="misc", value=text[11], inline=False)
		embed.add_field(name="for the rest of the helptext, ", value=text[-1], inline=False)
		await message.channel.send(embed=embed)
	elif cc+'admin' in message.content:
		embed=discord.Embed(title="How to use stats boye - admin", color=0x288D1)
		embed.add_field(name="about", value=text[12], inline=False)
		embed.add_field(name="for the rest of the helptext, ", value=text[-1], inline=False)
		await message.channel.send(embed=embed)
	elif cc+'misc' in message.content:
		embed=discord.Embed(title="How to use stats boye - misc", color=0x288D1)
		embed.add_field(name="setting your own color!", value=text[13], inline=False)
		embed.add_field(name="for the rest of the helptext, ", value=text[-1], inline=False)
		await message.channel.send(embed=embed)
	elif cc+'cheatsheet' in message.content or cc+'cs' in message.content:
		embed=discord.Embed(title="How to use stats boye - cheatsheet", color=0x288D1)
		embed.add_field(name="commands", value=text[-2], inline=False)
		await message.channel.send(embed=embed)
	else:
		embed=discord.Embed(title="How to use stats boye", color=0x288D1)
		embed.add_field(name="for the helptext, ", value=text[-1], inline=False)
		await message.channel.send(embed=embed)

	return True