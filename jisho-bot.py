# Help from https://discordpy.readthedocs.io/en/stable/
# Help from https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py
# Help from https://stackoverflow.com/a/1695199/

import discord
import requests
import urllib
import sys
from messageState import *
from discord.ext import commands

# todo list
#  cache improvements
#  command shortcuts
#  use local image
#  slash commands?
#  work in dms

# "Constants"
__TOKEN_FILENAME = 'token.txt'
__BOT_DESC = 'wip bot for jisho.org'
__JISHOHOME_URL = 'https://jisho.org'
__API_SEARCH_STEM = 'https://jisho.org/api/v1/search/words?keyword={query}'
__RESULTS_PER_PAGE = 5
__STATUS_OK = 200
__EMOJI_NUMS = {1: ':one:', 2: ':two:', 3: ':three:', 4: ':four:', 5: ':five:'}
__PING_RESPONSE = ':ping_pong: Pong! :ping_pong:'
__ERROR_BADSTATUS_STEM = 'Bad response status - expected 200 OK, got {status} instead'
__ERROR_INDEXERROR_STEM = 'Unable to find result number {number} for {query}'

# Reaction emojis
__REACT_ARROW_LEFT = '◀'
__REACT_ARROW_RIGHT = '▶'
__REACT_NUM_ONE = '1️⃣'
__REACT_NUM_TWO = '2️⃣'
__REACT_NUM_THREE = '3️⃣'
__REACT_NUM_FOUR = '4️⃣'
__REACT_NUM_FIVE = '5️⃣'
__REACT_X = '❌'
__REACTS_ARROWS = [__REACT_ARROW_LEFT, __REACT_ARROW_RIGHT]
__REACTS_NUMS = [__REACT_NUM_ONE, __REACT_NUM_TWO, __REACT_NUM_THREE, __REACT_NUM_FOUR, __REACT_NUM_FIVE]
__REACTS_ALL = __REACTS_ARROWS + __REACTS_NUMS + [__REACT_X]

# Command strings
__COMMAND_PREFIX = '!jisho'

__COMMAND_HELP = 'help'
__COMMAND_HELP_DESC = f'`{__COMMAND_PREFIX} {__COMMAND_HELP}` - Shows this help message'

__COMMAND_SEARCH = 'search'
__COMMAND_SEARCH_DESC = f'`{__COMMAND_PREFIX} {__COMMAND_SEARCH} <query>` - Searches jisho.org for `query`, shows first five results'

__COMMAND_DETAILS = 'details'
__COMMAND_DETAILS_DESC = f'`{__COMMAND_PREFIX} {__COMMAND_DETAILS} <num> <query>` - Shows details for the `num`th result for `query`'

__COMMAND_PING = 'ping'
__COMMAND_PING_DESC = f'`{__COMMAND_PREFIX} {__COMMAND_PING}` - Pings jisho-bot to respond with a pong'

# Embed constants
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
__EMBED_HELP_FIELD_LOOKUP_VALUE = '\n'.join([__COMMAND_SEARCH_DESC, __COMMAND_DETAILS_DESC])
__EMBED_HELP_FIELD_UTILITY_NAME = '__Utility commands__'
__EMBED_HELP_FIELD_UTILITY_VALUE = '\n'.join([__COMMAND_HELP_DESC, __COMMAND_PING_DESC])


__EMBED_SEARCH_TITLE_STEM = 'jisho.org search results for {query}'
__EMBED_SEARCH_DESCRIPTION_STEM = '*Showing results {start} to {end} (out of {total})*\n'
__EMBED_SEARCH_DESCRIPTION_NORESULTS = '*Sorry, no results were found*'
__EMBED_SEARCH_RESULT_FORMAT = '{emoji}: {result}\n'
__EMBED_SEARCH_URL_STEM = 'https://jisho.org/search/{query}'
__EMBED_SEARCH_FOOTER = 'Use the reacts for more actions\nPowered by jisho.org\'s beta API'

__EMBED_DETAILS_TITLE_STEM = 'jisho.org entry for {slug}'
__EMBED_DETAILS_URL_STEM = 'https://jisho.org/word/{slug}'
__EMBED_DETAILS_FOOTER_STEM = 'jisho.org entry data from {sources}\nPowered by jisho.org\'s beta API'
__EMBED_DETAILS_FIELD_WORD_NAME = '__Word__'
__EMBED_DETAILS_FIELD_TAGS_NAME = '__Tags__'
__EMBED_DETAILS_FIELD_DEFINITIONS_NAME = '__Definition(s)__'
__EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME = '__Defintions(s) *(some results have been truncated)*__'
__EMBED_DETAILS_FIELD_OTHERFORMS_NAME = '__Other forms__'
__EMBED_DETAILS_TAGS_COMMON = 'Common word'
__EMBED_DETAILS_TAGS_JLPTLEVEL_STEM = 'JLPT N{level}'
__EMBED_DETAILS_TAGS_WKURL_STEM = 'https://www.wanikani.com/vocabulary/{vocab}'
__EMBED_DETAILS_TAGS_WKLEVEL_STEM = 'WaniKani level {level}'
__EMBED_DETAILS_TAGS_WANIKANI_STEM = f'[{__EMBED_DETAILS_TAGS_WKLEVEL_STEM}]({__EMBED_DETAILS_TAGS_WKURL_STEM})'
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
                await _addreactions_many(bot_message, response_json)
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
        await _report_error(message.channel, repr(e))


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
        if reaction.emoji == __REACT_X:
            await reaction.message.delete()

        # Show result details
        if reaction.emoji in __REACTS_NUMS:
            number = __REACTS_NUMS.index(reaction.emoji)
            messagestate = cache[reaction.message]
            new_embed = _command_details_fromjson(number + messagestate.offset, messagestate.query, messagestate.response)
            await reaction.message.edit(embed=new_embed)
            # await _removereactions_selection(reaction.message)
            await reaction.message.clear_reactions()  # fixme another way to do this?
            await _addreactions_few(reaction.message)
            cache.remove(reaction.message)

        # Arrow left/right
        if reaction.emoji in __REACTS_ARROWS:
            delta = (-__RESULTS_PER_PAGE, __RESULTS_PER_PAGE)[reaction.emoji == __REACT_ARROW_RIGHT]
            messagestate = cache[reaction.message]
            if not 0 <= messagestate.offset + delta < len(messagestate.response['data']):
                return
            cache[reaction.message].offset += delta
            new_embed, _, _ = _command_search_fromjson(messagestate.query, messagestate.response, messagestate.offset)
            await reaction.message.edit(embed=new_embed)
            await reaction.message.remove_reaction(reaction.emoji, user)

    except Exception as e:
        await _report_error(reaction.message.channel, repr(e))


async def _addreactions_few(message):
    await message.add_reaction(__REACT_X)


async def _addreactions_many(message, response_json):
    results = _get_results_list(response_json)
    many_pages = len(results) > __RESULTS_PER_PAGE

    if many_pages:
        await message.add_reaction(__REACT_ARROW_LEFT)

    for reaction in __REACTS_NUMS[:min(5, len(results))]:
        await message.add_reaction(reaction)

    if many_pages:
        await message.add_reaction(__REACT_ARROW_RIGHT)

    await message.add_reaction(__REACT_X)


def command_help():
    # Build embed
    embed_dict = {
        'title':    __EMBED_HELP_TITLE,
        'color':    __EMBED_COLOR_BOT,
        'footer':   {'text': __EMBED_HELP_FOOTER},
        'fields':   [{'name': __EMBED_HELP_FIELD_ABOUT_NAME, 'value': __EMBED_HELP_FIELD_ABOUT_VALUE, 'inline': False},
                     {'name': __EMBED_HELP_FIELD_LOOKUP_NAME, 'value': __EMBED_HELP_FIELD_LOOKUP_VALUE, 'inline': False},
                     {'name': __EMBED_HELP_FIELD_UTILITY_NAME, 'value': __EMBED_HELP_FIELD_UTILITY_VALUE, 'inline': False}]
    }
    return discord.Embed.from_dict(embed_dict)


def command_search(search_query):
    # Communicate with jisho's beta API
    response_json = _api_call(search_query)

    return _command_search_fromjson(search_query, response_json, 0)


def _command_search_fromjson(search_query, response_json, start_from):
    # Header for search results list
    results_json = _get_results_list(response_json)
    end_at = min(start_from + __RESULTS_PER_PAGE, len(results_json))
    reply_message = __EMBED_SEARCH_DESCRIPTION_STEM.format(start=start_from + 1, end=end_at, total=len(results_json))

    # Format each line with the react emoji as well as the kanji + pronunciation (if possible)
    for i in range(start_from, end_at):
        emoji = __EMOJI_NUMS[i % __RESULTS_PER_PAGE + 1]
        readings = _get_readings_list(results_json[i])
        readable_word = _form_readable(readings[0])
        reply_message += __EMBED_SEARCH_RESULT_FORMAT.format(emoji=emoji, result=readable_word)

    # Change response message if there are no results
    if not len(results_json):
        reply_message = __EMBED_SEARCH_DESCRIPTION_NORESULTS

    # Build embed
    embed_dict = {
        'title':        __EMBED_SEARCH_TITLE_STEM.format(query=search_query),
        'description':  reply_message.strip(),
        'url':          __EMBED_SEARCH_URL_STEM.format(query=urllib.parse.quote(search_query, safe="")),
        'color':        __EMBED_COLOR_JISHO,
        'footer':       {'text': __EMBED_SEARCH_FOOTER},
        'thumbnail':    {'url': __EMBED_THUMBNAIL_JISHO},
    }

    return discord.Embed.from_dict(embed_dict), response_json, bool(len(results_json))


def command_details(number, search_query):
    # Communicate with jisho's beta API
    response_json = _api_call(search_query)

    if number < 0 or number >= len(_get_results_list(response_json)):
        raise IndexError(__ERROR_INDEXERROR_STEM.format(number=number + 1, query=search_query))

    return _command_details_fromjson(number, search_query, response_json)


def _command_details_fromjson(number, search_query, response_json):

    details_json: dict = _get_results_list(response_json)[number]
    readings = _get_readings_list(details_json)

    # Get kanji (if exists) and reading
    word = _form_readable(readings[0]) + '\n'

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

    # Check if word is listed as common
    if details_json['is_common']:
        tags += [__EMBED_DETAILS_TAGS_COMMON]

    # Apparently a single word can have multiple JLPT levels, choose the largest/easiest one (see 行く)
    if len(details_json['jlpt']):
        max_level = 0
        for level in details_json['jlpt']:
            max_level = max(max_level, int(level[-1]))
        tags += [__EMBED_DETAILS_TAGS_JLPTLEVEL_STEM.format(level=max_level)]

    # Get wanikani levels, assuming all tags are wanikani tags
    for entry in details_json['tags']:
        if not entry.startswith('wanikani'):
            _log_message(f'Unexpected tag: {entry}')
            continue

        wk_level = int(entry[len('wanikani'):])
        wk_vocab = details_json["japanese"][0]["word"]  # fixme not guaranteed to always work?
        tags += [__EMBED_DETAILS_TAGS_WANIKANI_STEM.format(level=wk_level, vocab=wk_vocab)]

    # Default no-tags message
    if not tags:
        tags = [__EMBED_DETAILS_TAGS_NONE]

    tags = '\n'.join(tags)

    # Get other forms
    many_forms = len(readings) > 1
    other_forms = '、'.join([_form_readable(form) for form in readings[1:]])

    # Get attribution data
    sources = [source for source, value in details_json['attribution'].items() if value]

    # Build embed
    embed_dict = {
        'title':        __EMBED_DETAILS_TITLE_STEM.format(slug=details_json["slug"]),
        'url':          __EMBED_DETAILS_URL_STEM.format(slug=details_json["slug"]),
        'color':        __EMBED_COLOR_JISHO,
        'footer':       {'text': __EMBED_DETAILS_FOOTER_STEM.format(sources=', '.join(sources))},
        'thumbnail':    {'url': __EMBED_THUMBNAIL_JISHO},
        'fields':       [{'name': __EMBED_DETAILS_FIELD_WORD_NAME, 'value': word, 'inline': True},
                         {'name': __EMBED_DETAILS_FIELD_TAGS_NAME, 'value': tags, 'inline': True},
                         {'name': (__EMBED_DETAILS_FIELD_DEFINITIONS_NAME, __EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME)[definitions_truncated], 'value': definitions, 'inline': False}]
                        + ([], [{'name': __EMBED_DETAILS_FIELD_OTHERFORMS_NAME, 'value': other_forms, 'inline': False}])[many_forms]
    }
    return discord.Embed.from_dict(embed_dict)


def command_ping():
    return __PING_RESPONSE


def _api_call(query):  # type: (str) -> dict
    """
    Helper method to do jisho.org's API call
    :param query: search query
    :return: JSON response
    :raises: ValueError if status code is not 200 OK
    """
    response = requests.get(__API_SEARCH_STEM.format(query=query)).json()

    if response['meta']['status'] != __STATUS_OK:
        raise ValueError(__ERROR_BADSTATUS_STEM.format(status=response["meta"]["status"]))

    return response


def _get_results_list(response_json):  # type: (dict) -> list
    """
    Helper method to get the list of search results from the response JSON (in case format changes later)
    :param response_json: response JSON returned from API
    :return: list of responses
    """
    return response_json['data']


def _get_readings_list(details_json):  # type: (dict) -> list
    """
    Helper method to get the list of readings for a search result
    :param details_json: search result JSON
    :return: list of readings (dicts)
    """
    return details_json['japanese']


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