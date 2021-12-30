import discord
from discord.ext import commands
# from discord_slash import SlashCommand

# Read token from file
token_file = open('token-test.txt', 'r')  # fixme testing
token = token_file.read().strip()

# Set up bot, slash commands
bot = commands.Bot(command_prefix="$jisho ")  # fixme testing
# slash = SlashCommand(bot, override_type=True)
bot.load_extension("jisho-bot-cog")
bot.run(token)
