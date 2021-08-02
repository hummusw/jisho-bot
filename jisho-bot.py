# Help from https://discordpy.readthedocs.io/en/stable/
# Help from https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py
# Help from https://stackoverflow.com/a/1695199/
import traceback

import discord
import requests
import urllib
import sys
from messageState import *
from discord.ext import commands

# todo list
#  multi-threading?
#  timed cache removals
#  slash commands?
#  better logging
#  better wk
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
__ERROR_INCORRECTARGS_STEM = 'Incorrect arguments - correct syntax is {syntax}'
__CACHE_MAXSIZE = 10
__MESSAGE_LOGIN_STEM = 'Logged in as {user}'
__MESSAGE_LOGCOMMAND_STEM = 'jisho-bot command by {user}: {command}'

# Reaction emojis
__REACT_ARROW_LEFT = '◀'
__REACT_ARROW_RIGHT = '▶'
__REACT_NUM_ONE = '1️⃣'
__REACT_NUM_TWO = '2️⃣'
__REACT_NUM_THREE = '3️⃣'
__REACT_NUM_FOUR = '4️⃣'
__REACT_NUM_FIVE = '5️⃣'
__REACT_RETURN = '↩'
__REACT_X = '❌'
__REACTS_ARROWS = [__REACT_ARROW_LEFT, __REACT_ARROW_RIGHT]
__REACTS_NUMS = [__REACT_NUM_ONE, __REACT_NUM_TWO, __REACT_NUM_THREE, __REACT_NUM_FOUR, __REACT_NUM_FIVE]
__REACTS_ALL = __REACTS_ARROWS + __REACTS_NUMS + [__REACT_RETURN, __REACT_X]

# Command strings
__COMMAND_PREFIX = '!jisho'
# __COMMAND_PREFIX_ALIAS = '!j'

__COMMAND_HELP = 'help'
__COMMAND_HELP_ALIAS = 'h'
__COMMAND_HELP_SYNTAX = f'`{__COMMAND_PREFIX} {__COMMAND_HELP}`'
__COMMAND_HELP_DESC = f'{__COMMAND_HELP_SYNTAX} - Shows this help message - *alias: `{__COMMAND_HELP_ALIAS}`*'

__COMMAND_SEARCH = 'search'
__COMMAND_SEARCH_ALIAS = 's'
__COMMAND_SEARCH_SYNTAX = f'`{__COMMAND_PREFIX} {__COMMAND_SEARCH} <query>`'
__COMMAND_SEARCH_DESC = f'{__COMMAND_SEARCH_SYNTAX} - Searches jisho.org for `query` - *alias: `{__COMMAND_SEARCH_ALIAS}`*'

__COMMAND_DETAILS = 'details'
__COMMAND_DETAILS_ALIAS = 'd'
__COMMAND_DETAILS_SYNTAX = f'`{__COMMAND_PREFIX} {__COMMAND_DETAILS} <num> <query>`'
__COMMAND_DETAILS_DESC = f'{__COMMAND_DETAILS_SYNTAX} - Shows details for the `num`th result for `query` - *alias: `{__COMMAND_DETAILS_ALIAS}`*'

__COMMAND_PING = 'ping'
__COMMAND_PING_ALIAS = 'p'
__COMMAND_PING_SYNTAX = f'`{__COMMAND_PREFIX} {__COMMAND_PING}`'
__COMMAND_PING_DESC = f'{__COMMAND_PING_SYNTAX} - Pings jisho-bot to respond with a pong - *alias: `{__COMMAND_PING_ALIAS}`*'

__UNKNOWN_RESPONSE = f'Unrecognized command, try `{__COMMAND_PREFIX} {__COMMAND_HELP}` to see a list of recognized commands'

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

cache = MessageCache(__CACHE_MAXSIZE)

# # Bot commands setup (?)
# intents = discord.Intents.default()
# intents.members = True
#
# bot = commands.Bot(command_prefix='?', description=__BOT_DESC, intents=intents)


@client.event
async def on_ready():  # type: () -> None
    """
    Log a short message on log in
    :return: Nothing
    """
    _log_message(__MESSAGE_LOGIN_STEM.format(user=client.user))


@client.event
async def on_message(message):  # type: (discord.Message) -> None
    """
    Look at every message that gets sent to see if something should be done

    :param message: new message sent
    :return: Nothing
    """
    # Ignore messages from self
    if message.author == client.user:
        return

    # Tokenize message
    command_tokens = message.content.rstrip().split()

    # Log commands for jisho-bot, ignore others
    if command_tokens[0] == __COMMAND_PREFIX:
        _log_message(__MESSAGE_LOGCOMMAND_STEM.format(user=message.author, command=message.content))
    else:
        return

    try:
        # No command - suggest help
        if len(command_tokens) == 1:
            await message.channel.send(command_unknown())

        # Testing - respond to messages "!jisho ping" with "pong"
        if command_tokens[1] in (__COMMAND_PING, __COMMAND_PING_ALIAS):
            await message.channel.send(command_ping())

        # Command - search - look for responses from jisho.org api
        elif command_tokens[1] in (__COMMAND_SEARCH, __COMMAND_SEARCH_ALIAS):
            if len(command_tokens) < 3:
                raise SyntaxError(__ERROR_INCORRECTARGS_STEM.format(syntax=__COMMAND_SEARCH_SYNTAX))

            query = ' '.join(command_tokens[2:])

            embed, response_json, found_results = command_search(query)
            bot_message = await message.channel.send(embed=embed)
            if found_results:
                await _addreactions_search(bot_message, response_json)
            else:
                await _addreactions_xonly(bot_message)

            await cache.insert(MessageStateQuery(message.author, query, response_json, bot_message, 0, _cache_cleanup))

        # Command - help - shows help message
        elif command_tokens[1] in (__COMMAND_HELP, __COMMAND_HELP_ALIAS):
            embed = command_help()
            bot_message = await message.channel.send(embed=embed)
            await _addreactions_xonly(bot_message)
            await cache.insert(MessageState(message.author, bot_message, _cache_cleanup))

        # Command - details - show result details
        elif command_tokens[1] in (__COMMAND_DETAILS, __COMMAND_DETAILS_ALIAS):
            if len(command_tokens) < 4:
                raise SyntaxError(__ERROR_INCORRECTARGS_STEM.format(syntax=__COMMAND_DETAILS_SYNTAX))

            try:
                number = int(command_tokens[2]) - 1
            except ValueError:
                raise SyntaxError(__ERROR_INCORRECTARGS_STEM.format(syntax=__COMMAND_DETAILS_SYNTAX))

            query = ' '.join(command_tokens[3:])

            embed, response_json = command_details(number, query)
            bot_message = await message.channel.send(embed=embed)
            await _addreactions_details(bot_message)
            await cache.insert(MessageStateQuery(message.author, message.content, response_json, bot_message, number - (number % __RESULTS_PER_PAGE), _cache_cleanup))

        # Unknown command - suggest help
        else:
            await message.channel.send(command_unknown())

    except Exception as e:
        await _report_error(message.channel, message.author, str(e))


@client.event
async def on_reaction_add(reaction, user):  # type: (discord.Reaction, discord.User) -> None
    """
    Look at every reaction to see what action should be performed

    :param reaction: Reaction added
    :param user: User who reacted
    :return: Nothing
    """
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
        # Ignore reactions by users who are not the original author
        messagestate = cache[reaction.message]
        if user != messagestate.author:
            print(f'ignoring reaction ({user} != {messagestate.author})')
            return

        # Remove messages that *any* user reacts ❌ to
        if reaction.emoji == __REACT_X:
            await cache.remove(reaction.message)
            await reaction.message.delete()

        # Show result details
        if reaction.emoji in __REACTS_NUMS:
            number = __REACTS_NUMS.index(reaction.emoji)

            # Ignore invalid indexes
            if number + messagestate.offset >= len(_get_results_list(messagestate.response)):
                return

            new_embed = _command_details_fromjson(number + messagestate.offset, messagestate.query, messagestate.response)
            await reaction.message.edit(embed=new_embed)
            await _removereactions_all(reaction.message)
            await _addreactions_details(reaction.message)

        # Arrow left/right
        if reaction.emoji in __REACTS_ARROWS:
            delta = (-__RESULTS_PER_PAGE, __RESULTS_PER_PAGE)[reaction.emoji == __REACT_ARROW_RIGHT]

            # Ignore page changes that would go out of bounds
            if not 0 <= messagestate.offset + delta < len(messagestate.response['data']):
                return

            cache[reaction.message].offset += delta
            new_embed = _command_search_fromjson(messagestate.query, messagestate.response, messagestate.offset)
            await reaction.message.edit(embed=new_embed)
            await reaction.message.remove_reaction(reaction.emoji, user)

        # Go back
        if reaction.emoji == __REACT_RETURN:
            new_embed = _command_search_fromjson(messagestate.query, messagestate.response, messagestate.offset)
            await reaction.message.edit(embed=new_embed)
            await _removereactions_all(reaction.message)
            await _addreactions_search(reaction.message, messagestate.response)

    except Exception as e:
        await _report_error(reaction.message.channel, reaction.message.author, str(e))


async def _addreactions_xonly(message):  # type: (discord.Message) -> None
    """
    Adds an x reaction to clear a sent embed

    :param message: Message to add reaction to
    :return: Nothing
    """
    await message.add_reaction(__REACT_X)


async def _addreactions_details(message):  # type: (discord.Message) -> None
    """
    Adds a return and an x react to a search result details message

    :param message: Message to add reactions to
    :return: Nothing
    """
    await message.add_reaction(__REACT_RETURN)
    await message.add_reaction(__REACT_X)


async def _addreactions_search(message, response_json):  # type: (discord.Message, dict) -> None
    """
    Adds left and right arrows (if needed), numbers (as appropriate), and an x react to a search results message

    :param message: Message to add reactions to
    :param response_json: response json to find what reactions are needed
    :return: Nothing
    """
    results = _get_results_list(response_json)
    many_pages = len(results) > __RESULTS_PER_PAGE

    if many_pages:
        await message.add_reaction(__REACT_ARROW_LEFT)

    # Add five number reactions unless there are a fewer number of search results
    for reaction in __REACTS_NUMS[:min(__RESULTS_PER_PAGE, len(results))]:
        await message.add_reaction(reaction)

    if many_pages:
        await message.add_reaction(__REACT_ARROW_RIGHT)

    await message.add_reaction(__REACT_X)


async def _removereactions_all(message):  # type: (discord.Message) -> None
    """
    Removes all reactions from a message

    :param message: Message to remove reactions from
    :return: Nothing
    """
    await message.clear_reactions()


# Until there are other things to do when removing from cache, this works
_cache_cleanup = _removereactions_all


def command_help():  # type: () -> discord.Embed
    """
    Builds a help embed

    :return: Help embed
    """
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


def command_search(search_query):  # type: (str) -> (discord.Embed, dict, bool)
    """
    Queries jisho.org api to get a response json to show search results

    :param search_query: query for jisho.org search
    :return: search embed, response json, boolean (True if results were found, False otherwise)
    """
    # Communicate with jisho's beta API
    response_json = _api_call(search_query)

    return _command_search_fromjson(search_query, response_json, 0), response_json, bool(len(_get_results_list(response_json)))


def _command_search_fromjson(search_query, response_json, start_from):  # type: (str, dict, int) -> discord.Embed
    """
    Builds a search results embed from a response json

    :param search_query: query for jisho.org search
    :param response_json: response from jisho.org api
    :param start_from: shows search results starting at this offset
    :return: search embed
    """
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

    return discord.Embed.from_dict(embed_dict)


def command_details(number, search_query):  # type: (int, str) -> (discord.Embed, dict)
    """
    Queries jisho.org api to shows details for a search query

    :param number: the result number to show details for (zero-indexed)
    :param search_query: query for jisho.org search
    :return: details embed, response json
    """
    # Communicate with jisho's beta API
    response_json = _api_call(search_query)

    if number < 0 or number >= len(_get_results_list(response_json)):
        raise IndexError(__ERROR_INDEXERROR_STEM.format(number=number + 1, query=search_query))

    return _command_details_fromjson(number, search_query, response_json), response_json


def _command_details_fromjson(number, search_query, response_json):  # type: (int, str, dict) -> discord.Embed
    """
    Builds a details embed from a response json

    :param number: the result number to show details for (zero-indexed)
    :param search_query: query for jisho.org search
    :param response_json: response from jisho.org api
    :return: details embed
    """

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
        if def_json.get('tags'):
            extras += [', '.join(def_json['tags'])]
        if def_json.get('restrictions'):
            extras += ['Only applies to ' + ', '.join(def_json['restrictions'])]
        if def_json.get('see_also'):
            extras += ['See also ' + ', '.join(def_json['see_also'])]
        if def_json.get('antonyms'):
            extras += ['Antonym: ' + ', '.join(def_json['antonyms'])]
        if def_json.get('source'):  # todo find example of this
            _log_message(f'Found example of source extra, in result {number} for {search_query}')
            extras += ['Source: ' + ', '.join(def_json['source'])]
        if def_json.get('info'):  # used for random notes (see 行く, definition 2)
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
    if details_json.get('is_common'):  # apparently some entries don't have a is_common key
        tags += [__EMBED_DETAILS_TAGS_COMMON]

    # Apparently a single word can have multiple JLPT levels, choose the largest/easiest one (see 行く)
    if len(details_json.get('jlpt', [])):
        max_level = 0
        for level in details_json['jlpt']:
            max_level = max(max_level, int(level[-1]))
        tags += [__EMBED_DETAILS_TAGS_JLPTLEVEL_STEM.format(level=max_level)]

    # Get wanikani levels, assuming all tags are wanikani tags
    for entry in details_json.get('tags', []):
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
                         {'name': __EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME if definitions_truncated else __EMBED_DETAILS_FIELD_DEFINITIONS_NAME, 'value': definitions, 'inline': False}]
                        + ([{'name': __EMBED_DETAILS_FIELD_OTHERFORMS_NAME, 'value': other_forms, 'inline': False}] if many_forms else [])
    }
    return discord.Embed.from_dict(embed_dict)


def command_ping():  # type: () -> str
    """
    Returns ping response

    :return: ping response
    """
    return __PING_RESPONSE


def command_unknown():  # type: () -> str
    """
    Returns unknown command response

    :return: ping response
    """
    return __UNKNOWN_RESPONSE


def _api_call(query):  # type: (str) -> dict
    """
    Helper method to do jisho.org's API call

    :param query: search query
    :return: JSON response
    :raises ValueError: status code is not 200 OK
    """
    response_json = requests.get(__API_SEARCH_STEM.format(query=query)).json()
    status_code = response_json['meta']['status']

    if status_code != __STATUS_OK:
        raise ValueError(__ERROR_BADSTATUS_STEM.format(status=status_code))

    return response_json


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


async def _report_error(channel, author, error_message):  # type: (discord.TextChannel, discord.User, str) -> None
    """
    Reports an error by sending an embed, as well as printing to stderr

    :param channel: channel to send error report to
    :param author: original author that caused error
    :param error_message: reported error
    :return: Nothing
    """
    _log_error()

    embed_dict = {
        'title':        __EMBED_ERROR_TITLE,
        'description':  error_message,
        'color':        __EMBED_COLOR_ERROR,
        'footer':       {'text': __EMBED_ERROR_FOOTER}
    }

    embed = discord.Embed.from_dict(embed_dict)

    bot_message = await channel.send(embed=embed)
    await bot_message.add_reaction('❌')
    await cache.insert(MessageState(author, bot_message, _cache_cleanup))


def _log_message(message):  # type: (str) -> None
    """
    Logs a message to stdout  # todo change to somethine else other than stdout

    :param message: message to log
    :return: Nothing
    """
    print(message)


def _log_error():  # type: () -> None
    """
    Logs error traceback and message to stderr # todo change to something else other than console

    :return: Nothing
    """
    traceback.print_exc(limit=3, file=sys.stderr)


# @bot.command(description="Search jisho.org for results")
# async def search(ctx, query):
#     await ctx.send("test")


# Read token from file, run client
token_file = open(__TOKEN_FILENAME, 'r')
token = token_file.read().strip()
client.run(token)
