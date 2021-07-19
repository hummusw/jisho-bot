# Help from https://discordpy.readthedocs.io/en/stable/
# Help from https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py
# Help from https://stackoverflow.com/a/1695199/

import discord
import requests
import urllib
import sys
from messageState import *
from discord.ext import commands

# "Constants"
__TOKEN_FILENAME = 'token.txt'
__BOT_DESC = 'wip bot for jisho.org'
__JISHOHOME_URL = 'https://jisho.org'
__API_URL = 'https://jisho.org/api/v1/search/words?keyword='
__STATUS_OK = 200
__EMOJI_NUMS = {1: ':one:', 2: ':two:', 3: ':three:', 4: ':four:', 5: ':five:'}
__PING_RESPONSE = ':ping_pong: Pong! :ping_pong:'
__ERROR_BADSTATUS_STEM = 'Bad response status - expected 200 OK, got '
__ERROR_INDEXERROR_STEM = 'Unable to find the search result with number '

# Command strings
__COMMAND_PREFIX = '!jisho'
__COMMAND_HELP = 'help'
__COMMAND_SEARCH = 'search'
__COMMAND_DETAILS = 'details'
__COMMAND_PING = 'ping'

# Embed constants
# __EMBED_AUTHOR_NAME = 'jisho-bot'
# __EMBED_AUTHOR_URL = 'https://jisho.org'

__EMBED_THUMBNAIL_JISHO = 'https://assets.jisho.org/assets/touch-icon-017b99ca4bfd11363a97f66cc4c00b1667613a05e38d08d858aa5e2a35dce055.png'

__EMBED_COLOR_JISHO = 0x3edd00
__EMBED_COLOR_BOT = 0x5865f2
__EMBED_COLOR_ERROR = 0xff0000

__EMBED_FIELD_MAXLENGTH = 1024

__EMBED_HELP_TITLE = 'jisho-bot help'
__EMBED_HELP_FOOTER = 'jisho-bot is not affiliated with jisho.org in any way.'
__EMBED_HELP_FIELD_ABOUT_NAME = '__About__'
__EMBED_HELP_FIELD_ABOUT_VALUE = 'jisho-bot is currently a work-in-progress bot that searches jisho.org directly ' \
                                 + f'from Discord, powered by [jisho.org]({__JISHOHOME_URL})\'s beta API.'
__EMBED_HELP_FIELD_LOOKUP_NAME = '__Lookup commands__'
__EMBED_HELP_FIELD_LOOKUP_VALUE = '`!jisho search <query>` - Searches jisho.org for `query`, shows first five results\n'\
                                  + '`!jisho details <num> <query>` - Shows details for the `num`th result for `query`'
__EMBED_HELP_FIELD_UTILITY_NAME = '__Utility commands__'
__EMBED_HELP_FIELD_UTILITY_VALUE = '`!jisho help` - Shows this help message\n' \
                                   + '`!jisho ping` - Pings jisho-bot to respond with a pong'


__EMBED_SEARCH_TITLE_STEM = 'jisho.org search results for '
__EMBED_SEARCH_DESCRIPTION_STEM = '*Showing results {start} to {end} (out of {total})*\n'
__EMBED_SEARCH_DESCRIPTION_NORESULTS = '*Sorry, no results were found*'
__EMBED_SEARCH_URL_STEM = 'https://jisho.org/search/'
__EMBED_SEARCH_FOOTER = 'Use the reacts for more actions (work in progress)\nPowered by jisho.org\'s beta API'

__EMBED_DETAILS_TITLE_STEM = 'jisho.org entry for '
__EMBED_DETAILS_URL_STEM = 'https://jisho.org/word/'
__EMBED_DETAILS_ATTRIBUTION_STEM = 'jisho.org entry data from '
__EMBED_DETAILS_FOOTER_ENDER = 'Powered by jisho.org\'s beta API'
__EMBED_DETAILS_FIELD_WORD_NAME = '__Word__'
__EMBED_DETAILS_FIELD_TAGS_NAME = '__Tags__'
__EMBED_DETAILS_FIELD_DEFINITIONS_NAME = '__Definition(s)__'
__EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME = '__Defintions(s) *(some results have been truncated)*__'
__EMBED_DETAILS_FIELD_OTHERFORMS_NAME = '__Other forms__'
__EMBED_DETAILS_TAGS_COMMON = 'Common word'
__EMBED_DETAILS_TAGS_JLPTLEVEL_STEM = 'JLPT N'
__EMBED_DETAILS_TAGS_WKURL_STEM = 'https://www.wanikani.com/vocabulary/'
__EMBED_DETAILS_TAGS_WKLEVEL_STEM = 'WaniKani level '
__EMBED_DETAILS_TAGS_NONE = '*None*'

__EMBED_ERROR_TITLE = 'An error has occurred'
__EMBED_ERROR_FOOTER = 'Please report any unexpected errors'

client = discord.Client()

cache = MessageCacheNaive()

# # Bot commands setup (?)
# intents = discord.Intents.default()
# intents.members = True
#
# bot = commands.Bot(command_prefix='?', description=__BOT_DESC, intents=intents)

@client.event
async def on_ready():
    _log_message('Logged on as {0}!'.format(client.user))


@client.event
async def on_message(message):
    # Ignore messages from self
    if message.author == client.user:
        return

    if message.content.startswith(__COMMAND_PREFIX):
        _log_message('Message from {0.author}: {0.content}'.format(message))

    try:
        # Testing - respond to messages "!jisho ping" with "pong"
        if message.content == __COMMAND_PREFIX + ' ' + __COMMAND_PING:
            await message.channel.send(command_ping())

        # Command - search - look for responses from jisho.org api
        if message.content.startswith(__COMMAND_PREFIX + ' ' + __COMMAND_SEARCH + ' '):
            query = message.content[len(__COMMAND_PREFIX + ' ' + __COMMAND_SEARCH + ' '):]

            embed, response_json, found_results = command_search(query)
            bot_message = await message.channel.send(embed=embed)
            if found_results:
                await _addreactions_full(bot_message)
            else:
                await _addreactions_few(bot_message)

            cache.insert(MessageState(message.author, query, response_json, bot_message, 0))

        # Command - help - shows help message
        if message.content.startswith(__COMMAND_PREFIX + ' ' + __COMMAND_HELP):
            embed = command_help()
            bot_message = await message.channel.send(embed=embed)
            await _addreactions_few(bot_message)

        # Command - details - show result details
        if message.content.startswith(__COMMAND_PREFIX + ' ' + __COMMAND_DETAILS + ' '):
            query = message.content[len(__COMMAND_PREFIX + ' ' + __COMMAND_DETAILS + ' '):].strip()
            number = int(query.split()[0]) - 1
            query = query[len(query.split()[0]):].strip()

            embed = command_details(number, query)
            bot_message = await message.channel.send(embed=embed)
            await _addreactions_few(bot_message)

    except Exception as e:
        await _report_error(message.channel, str(e))


@client.event
async def on_reaction_add(reaction, user):
    # Ignore reactions to messages that aren't from the bot
    if not reaction.message.author == client.user:
        return

    # Ignore reactions made by the bot
    if user == client.user:
        return

    # Ignore reactions that the bot has not reacted with
    if client.user not in await reaction.users().flatten():
        return

    try:
        # Remove messages that *any* user reacts ❌ to  fixme only original user
        if reaction.emoji == '❌':
            await reaction.message.delete()

        # Show result details
        if reaction.emoji in ('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'):
            number = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'].index(reaction.emoji)
            messagestate = cache[reaction.message]
            new_embed = _command_details_fromjson(number + messagestate.offset, messagestate.query, messagestate.response)
            await reaction.message.edit(embed=new_embed)
            # await _removereactions_selection(reaction.message)
            await reaction.message.clear_reactions()  # fixme another way to do this?
            await _addreactions_few(reaction.message)
            cache.remove(reaction.message)

        # Page right
        if reaction.emoji == '▶':
            messagestate = cache[reaction.message]
            if len(messagestate.response['data']) <= messagestate.offset + 5:
                return
            cache[reaction.message].offset += 5
            new_embed, _, _ = _command_search_fromjson(messagestate.query, messagestate.response, messagestate.offset)
            await reaction.message.edit(embed=new_embed)
            await reaction.message.remove_reaction('▶', user)

        # Page left
        if reaction.emoji == '◀':
            messagestate = cache[reaction.message]
            if messagestate.offset - 5 < 0:
                return
            cache[reaction.message].offset -= 5
            new_embed, _, _ = _command_search_fromjson(messagestate.query, messagestate.response, messagestate.offset)
            await reaction.message.edit(embed=new_embed)
            await reaction.message.remove_reaction('◀', user)

    except Exception as e:
        await _report_error(reaction.message.channel, str(e))


async def _addreactions_few(message):
    await message.add_reaction('❌')


async def _addreactions_full(message):
    await message.add_reaction('◀')
    await message.add_reaction('1️⃣')
    await message.add_reaction('2️⃣')
    await message.add_reaction('3️⃣')
    await message.add_reaction('4️⃣')
    await message.add_reaction('5️⃣')
    await message.add_reaction('▶')
    await message.add_reaction('❌')

# clearing all seems to work better
# async def _removereactions_selection(message):
#     await message.remove_reaction('◀', client.user)
#     await message.remove_reaction('1️⃣', client.user)
#     await message.remove_reaction('2️⃣', client.user)
#     await message.remove_reaction('3️⃣', client.user)
#     await message.remove_reaction('4️⃣', client.user)
#     await message.remove_reaction('5️⃣', client.user)
#     await message.remove_reaction('▶', client.user)

def command_help():
    # Build embed
    embed_dict = {
        'title':    __EMBED_HELP_TITLE,
        'color':    __EMBED_COLOR_BOT,
        # 'author':   {'name': __EMBED_AUTHOR_NAME, 'url': __EMBED_AUTHOR_URL},
        'footer':   {'text': __EMBED_HELP_FOOTER},
        'fields':   [{'name': __EMBED_HELP_FIELD_ABOUT_NAME, 'value': __EMBED_HELP_FIELD_ABOUT_VALUE, 'inline': False},
                     {'name': __EMBED_HELP_FIELD_LOOKUP_NAME, 'value': __EMBED_HELP_FIELD_LOOKUP_VALUE, 'inline': False},
                     {'name': __EMBED_HELP_FIELD_UTILITY_NAME, 'value': __EMBED_HELP_FIELD_UTILITY_VALUE, 'inline': False}]
    }
    return discord.Embed.from_dict(embed_dict)


def command_search(search_query):
    # Communicate with jisho's beta API
    response_json = requests.get(__API_URL + search_query).json()

    if response_json['meta']['status'] != __STATUS_OK:
        raise ValueError(f'{__ERROR_BADSTATUS_STEM}{response_json["meta"]["status"]}')

    return _command_search_fromjson(search_query, response_json, 0)


def _command_search_fromjson(search_query, response_json, start_from):
    # Build response message
    results_json = response_json["data"]
    reply_message = __EMBED_SEARCH_DESCRIPTION_STEM.format(start=start_from + 1, end=min(start_from + 5, len(results_json)), total=len(results_json))

    try:
        for i in range(start_from, start_from + 5):
            reply_message += f'{__EMOJI_NUMS[i % 5 + 1]}: {_form_readable(results_json[i]["japanese"][0])}\n'
    except IndexError:
        pass

    # Change response message if there are no results
    if not len(results_json):
        reply_message = __EMBED_SEARCH_DESCRIPTION_NORESULTS

    # Build embed
    embed_dict = {
        'title':        f'{__EMBED_SEARCH_TITLE_STEM}{search_query}',
        'description':  reply_message.strip(),
        'url':          f'{__EMBED_SEARCH_URL_STEM}{urllib.parse.quote(search_query, safe="")}',
        'color':        __EMBED_COLOR_JISHO,
        'footer':       {'text': __EMBED_SEARCH_FOOTER},
        'thumbnail':    {'url': __EMBED_THUMBNAIL_JISHO},
        # 'author':       {'name': __EMBED_AUTHOR_NAME, 'url': __EMBED_AUTHOR_URL}  # this looks better without, honestly
    }

    return discord.Embed.from_dict(embed_dict), response_json, bool(len(results_json))


def command_details(number, search_query):
    # Communicate with jisho's beta API
    response_json = requests.get(__API_URL + search_query).json()

    if response_json['meta']['status'] != __STATUS_OK:
        raise ValueError(f'{__ERROR_BADSTATUS_STEM}{response_json["meta"]["status"]}')

    try:
        response_json["data"][number]
    except IndexError:
        raise IndexError(f'{__ERROR_INDEXERROR_STEM}{number + 1}')

    return _command_details_fromjson(number, search_query, response_json)


def _command_details_fromjson(number, search_query, response_json):

    details_json = response_json["data"][number]

    # Get kanji (if exists) and reading
    word = f'{_form_readable(details_json["japanese"][0])}\n'

    # Get definitions
    definitions_truncated = False
    definitions = []
    definitions_json = details_json['senses']
    for i in range(len(definitions_json)):
        def_json = definitions_json[i]

        # First add parts of speech, italicized
        definition = f'*{", ".join(def_json["parts_of_speech"])}*\n'

        # Then add definitions, numbered and bolded
        definition += f'**{i + 1}. {"; ".join(def_json["english_definitions"])}** '

        # Then add extras
        extras = []
        # Used for Wikipedia definitions, don't include
        # if details_json['links']:
        #     extras += ['Links: ' + ', '.join(details_json['links'])]
        if def_json['tags']:
            extras += [', '.join(def_json['tags'])]
        if def_json['restrictions']:
            extras += ['Only applies to ' + ', '.join(def_json['restrictions'])]
        if def_json['see_also']:
            extras += ['See also ' + ', '.join(def_json['see_also'])]
        if def_json['antonyms']:
            extras += ['Antonym: ' + ', '.join(def_json['antonyms'])]
        if def_json['source']:  # todo find example of this
            _log_message(f'Found example of source extra, in result {number} for {search_query}')
            extras += ['Source: ' + ', '.join(def_json['source'])]
        if def_json['info']:  # used for random notes (see 行く, definition 2)
            extras += [', '.join(def_json['info'])]
        definition += ', '.join(extras)

        # Check maximum length (entries such as 行く can go over this) before adding to list
        if len('\n'.join(definitions)) + 1 + len(definition) > __EMBED_FIELD_MAXLENGTH:
            definitions_truncated = True
            break
        else:
            definitions += [definition]

    definitions = '\n'.join(definitions)

    # Get tags (common, jlpt, wanikani)
    tags = []

    if details_json['is_common']:
        tags += [__EMBED_DETAILS_TAGS_COMMON]

    # Apparently a single word can have multiple JLPT levels, choose the largest/easiest one (see 行く)
    if len(details_json['jlpt']):
        max_level = 0
        for level in details_json['jlpt']:
            max_level = max(max_level, int(level[-1]))
        tags += [f'{__EMBED_DETAILS_TAGS_JLPTLEVEL_STEM}{max_level}']

    for entry in details_json['tags']:
        # Assuming all tags are WaniKani tags
        if not entry.startswith('wanikani'):
            _log_message(f'Unexpected tag: {entry}')
            continue

        wk_level = int(entry[len('wanikani'):])
        tags += [f'[{__EMBED_DETAILS_TAGS_WKLEVEL_STEM}{wk_level}]({__EMBED_DETAILS_TAGS_WKURL_STEM}{details_json["japanese"][0]["word"]})']  # fixme risky code

    if not tags:
        tags = [__EMBED_DETAILS_TAGS_NONE]

    tags = '\n'.join(tags)

    # Get other forms
    many_forms = len(details_json['japanese']) > 1
    other_forms = [_form_readable(form) for form in details_json['japanese'][1:]]
    other_forms = '、'.join(other_forms)

    # Get attribution data
    sources = [source for source, value in details_json['attribution'].items() if value]
    attribution = __EMBED_DETAILS_ATTRIBUTION_STEM + ', '.join(sources)

    # Build embed
    embed_dict = {
        'title':        f'{__EMBED_DETAILS_TITLE_STEM}{details_json["slug"]}',
        'url':          f'{__EMBED_DETAILS_URL_STEM}{details_json["slug"]}',
        'color':        __EMBED_COLOR_JISHO,
        'footer':       {'text': f'{attribution}\n{__EMBED_DETAILS_FOOTER_ENDER}'},
        'thumbnail':    {'url': __EMBED_THUMBNAIL_JISHO},
        # 'author':       {'name': __EMBED_AUTHOR_NAME, 'url': __EMBED_AUTHOR_URL},  # this looks better without, honestly
        'fields':       [{'name': __EMBED_DETAILS_FIELD_WORD_NAME, 'value': word, 'inline': True},
                         {'name': __EMBED_DETAILS_FIELD_TAGS_NAME, 'value': tags, 'inline': True},
                         {'name': (__EMBED_DETAILS_FIELD_DEFINITIONS_NAME, __EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME)[definitions_truncated], 'value': definitions, 'inline': False}]
                        + ([], [{'name': __EMBED_DETAILS_FIELD_OTHERFORMS_NAME, 'value': other_forms, 'inline': False}])[many_forms]
    }
    return discord.Embed.from_dict(embed_dict)


def command_ping():
    return __PING_RESPONSE
    # No X react here on purpose, since this is a text-only message


def _form_readable(form):  # type: (dict) -> str
    """
    Helper method to return a readable version of a form: kanji with reading if both exist, otherwise whichever one does
    :param form: dictionary with key 'reading' and possibly the key 'word'
    :return: string of kanji with reading or just reading, whichever is appropriate
    """
    if form.get('word') and form.get('reading'):
        return f'{form["word"]}（{form["reading"]}）'
    elif form.get('word'):
        return form['word']
    else:
        return form['reading']


async def _report_error(channel, error_message):  # type: (discord.TextChannel, str) -> None
    """
    Reports an error by sending an embed, as well as printing to stderr
    :param channel: channel to send error report to
    :param error_message: reported error
    :return:
    """
    _log_error(error_message)

    embed_dict = {
        'title':        __EMBED_ERROR_TITLE,
        'description':  error_message,
        'color':        __EMBED_COLOR_ERROR,
        'footer':       {'text': __EMBED_ERROR_FOOTER}
    }

    embed = discord.Embed.from_dict(embed_dict)

    bot_message = await channel.send(embed=embed)
    await bot_message.add_reaction('❌')


def _log_message(message):  # type: (str) -> None
    """
    Logs a message to stdout  # todo change to somethine else other than stdout
    :param message: message to log
    :return:
    """
    print(message)


def _log_error(message):  # type: (str) -> None
    """
    Logs an error to stderr # todo change to something else other than console
    :param message: error message to log
    :return:
    """
    print(message, file=sys.stderr)

# @bot.command(description="Search jisho.org for results")
# async def search(ctx, query):
#     await ctx.send("test")


# Read token from file, run client
token_file = open(__TOKEN_FILENAME, 'r')
token = token_file.read().strip()
client.run(token)