import sys

import discord
from discord.ext import commands
# from discord_slash import SlashCommand

# Default token file location
token_filename = 'token.txt'

if __name__ == '__main__':
    # Allow default token file location to be overriden through via command line argument
    if len(sys.argv) >= 2:
        token_filename = sys.argv[1]

    # Read token from file
    token = open(token_filename, 'r').read().strip()

    # Set up bot and run
    bot = commands.Bot(command_prefix="!jisho ")
    # slash = SlashCommand(bot, override_type=True)
    bot.load_extension("jisho-bot-cog")
    bot.run(token)
