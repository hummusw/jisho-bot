# Help from https://discordpy.readthedocs.io/en/stable/
# Help from https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py
# Help from https://stackoverflow.com/a/1695199/

# Discord imports
import discord
from discord.ext import commands
# from discord_slash import cog_ext, SlashContext

# Python imports
import urllib
import sys
import asyncio
import traceback
import aiohttp

# Custom imports
from jisho_bot_strings import *
from jisho_bot_constants import *
from messageState import *

# todo list
#  fail loudly (regression from Beta 1)
#  whats new
#  multi-threading?
#  slash commands?
#  better logging
#  better wk - wait for improvements in wk's search system https://www.wanikani.com/search?query=%s
#  work in dms
#  fix theoretical recursion limit exceeded error

# fixme change from (*args) to (*, arg)

class JishoCog(commands.Cog):
    def __init__(self, bot):  # type: (discord.ext.commands.bot) -> None
        self.bot = bot

        # Set up variables
        self.cache = MessageCache(CACHE_MAXSIZE)  # type: MessageCache
        self.session = aiohttp.ClientSession()  # type: aiohttp.ClientSession
        self.help_embed = self._command_help_embed()  # type: discord.Embed

        self._log_message(MESSAGE_LOGIN)

    def cog_unload(self):  # type: () -> None
        """
        Unloads cog, closing the aiohttp session
        """
        self._log_message(MESSAGE_LOGOUT)
        self.bot.loop.create_task(self.session.close())

    # Command functions - lookup

    @commands.command(name=COMMAND_SEARCH, aliases=[COMMAND_SEARCH_ALIAS], help=COMMAND_SEARCH_DESC_SHORT, description=HELP_DESCRIPTION_STEM.format(command=COMMAND_SEARCH))
    async def command_search(self, context, *query):  # type: (commands.context, *str) -> None
        """
        Searches jisho.org for <query>

        :param context: command context
        :param query: search query
        """
        # Verify query exists
        if not len(query):
            raise SyntaxError(ERROR_INCORRECTARGS_STEM.format(syntax=COMMAND_SEARCH_SYNTAX))

        query = ' '.join(query)

        # Build embed, send message
        embed, response_json, found_results = await self.command_search_embed(query)
        bot_message = await context.channel.send(embed=embed)

        # Add to message cache
        await self.cache.insert(
            MessageStateQuery(context.author, query, response_json, bot_message, 0, self._cache_cleanup))

        # Add reactions, wait for interaction
        if found_results:
            await self._addreactions_search(bot_message, response_json)
            await self._wait_search(bot_message)
        else:
            await self._addreactions_xonly(bot_message)
            await self._wait_nothing(bot_message)

    async def command_search_embed(self, search_query):  # type: (str) -> (discord.Embed, dict, bool)
        """
        Queries jisho.org api to get a response json to show search results

        :param search_query: query for jisho.org search
        :return: search embed, response json, boolean (True if results were found, False otherwise)
        """
        # Communicate with jisho's beta API
        response_json = await self._api_call(search_query)

        return self._command_search_embedfromjson(search_query, response_json, 0), response_json, bool(len(self._get_results_list(response_json)))

    def _command_search_embedfromjson(self, search_query, response_json, start_from):  # type: (str, dict, int) -> discord.Embed
        """
        Builds a search results embed from a response json

        :param search_query: query for jisho.org search
        :param response_json: response from jisho.org api
        :param start_from: shows search results starting at this offset
        :return: search embed
        """
        # Header for search results list
        results_json = self._get_results_list(response_json)
        end_at = min(start_from + RESULTS_PER_PAGE, len(results_json))
        reply_message = EMBED_SEARCH_DESCRIPTION_STEM.format(start=start_from + 1, end=end_at,
                                                                    total=len(results_json))

        # Format each line with the react emoji as well as the kanji + pronunciation (if possible)
        for i in range(start_from, end_at):
            emoji = EMOJI_NUMS[i % RESULTS_PER_PAGE + 1]
            readings = self._get_readings_list(results_json[i])
            readable_word = self._form_readable(readings[0])
            reply_message += EMBED_SEARCH_RESULT_FORMAT.format(emoji=emoji, result=readable_word)

        # Change response message if there are no results
        if not len(results_json):
            reply_message = EMBED_SEARCH_DESCRIPTION_NORESULTS

        # Build embed
        embed_dict = {
            'title': EMBED_SEARCH_TITLE_STEM.format(query=search_query),
            'description': reply_message.strip(),
            'url': EMBED_SEARCH_URL_STEM.format(query=urllib.parse.quote(search_query, safe="")),
            'color': EMBED_COLOR_JISHO,
            'footer': {'text': EMBED_SEARCH_FOOTER},
            'thumbnail': {'url': EMBED_THUMBNAIL_JISHO},
        }

        return discord.Embed.from_dict(embed_dict)

    @commands.command(name=COMMAND_DETAILS, aliases=[COMMAND_DETAILS_ALIAS], hidden=True)
    async def command_details(self, context, num, *query):  # type: (commands.context, str, *str) -> None
        """
        (Hidden) Shows details for <num>th result for <query>

        :param context: command context
        :param num: result number to show details for
        :param query: search query
        """
        # Verify the number of tokens, number is a number
        if len(query) == 0:
            raise SyntaxError(ERROR_INCORRECTARGS_STEM.format(syntax=COMMAND_DETAILS_SYNTAX))
        try:
            number = int(num) - 1
        except ValueError:
            raise SyntaxError(ERROR_INCORRECTARGS_STEM.format(syntax=COMMAND_DETAILS_SYNTAX))

        query = ' '.join(query)

        # Build embed, send message
        embed, response_json = await self._command_details_embed(number, query)
        bot_message = await context.channel.send(embed=embed)

        # Add to message cache
        await self.cache.insert(MessageStateQuery(context.author, query, response_json, bot_message,
                                                  number - (number % RESULTS_PER_PAGE), self._cache_cleanup))

        # Add reactions, wait for interaction
        await self._addreactions_details(bot_message)
        await self._wait_details(bot_message)

    async def _command_details_embed(self, number, search_query):  # type: (int, str) -> (discord.Embed, dict)
        """
        Queries jisho.org api to shows details for a search query

        :param number: the result number to show details for (zero-indexed)
        :param search_query: query for jisho.org search
        :return: details embed, response json
        """
        # Communicate with jisho's beta API
        response_json = await self._api_call(search_query)

        # Make sure the result number we're looking for exists
        if number < 0 or number >= len(self._get_results_list(response_json)):
            raise IndexError(ERROR_INDEXERROR_STEM.format(number=number + 1, query=search_query))

        return self._command_details_embedfromjson(number, search_query, response_json), response_json

    def _command_details_embedfromjson(self, number, search_query, response_json):  # type: (int, str, dict) -> discord.Embed
        """
        Builds a details embed from a response json

        :param number: the result number to show details for (zero-indexed)
        :param search_query: query for jisho.org search
        :param response_json: response from jisho.org api
        :return: details embed
        """

        details_json: dict = self._get_results_list(response_json)[number]
        readings = self._get_readings_list(details_json)

        # Get kanji (if exists) and reading
        word = self._form_readable(readings[0]) + '\n'

        # Get definitions
        definitions_truncated = False
        definitions = []
        definitions_json = details_json['senses']
        for i in range(len(definitions_json)):
            def_json = definitions_json[i]
            definition = ''

            # First add parts of speech, italicized if it exists
            if def_json.get('parts_of_speech'):
                definition += f'*{", ".join(def_json["parts_of_speech"])}*\n'

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
            if def_json.get('source'):  # used for words from other languages, see 加油
                extras += ['From ' + ', '.join([f"{source['language']} {source['word']}" for source in def_json['source']])]
            if def_json.get('info'):  # used for random notes (see 行く, definition 2)
                extras += [', '.join(def_json['info'])]
            definition += ', '.join(extras)

            # Check maximum length (entries such as 行く can go over this) before adding to list
            if len('\n'.join(definitions)) + 1 + len(definition) > EMBED_FIELD_MAXLENGTH:
                definitions_truncated = True
                break
            else:
                definitions += [definition]

        definitions = '\n'.join(definitions)

        # Get tags (common, jlpt, wanikani)
        tags = []

        # Check if word is listed as common
        if details_json.get('is_common'):  # apparently some entries don't have a is_common key
            tags += [EMBED_DETAILS_TAGS_COMMON]

        # Apparently a single word can have multiple JLPT levels, choose the largest/easiest one (see 行く)
        if len(details_json.get('jlpt', [])):
            max_level = 0
            for level in details_json['jlpt']:
                max_level = max(max_level, int(level[-1]))
            tags += [EMBED_DETAILS_TAGS_JLPTLEVEL_STEM.format(level=max_level)]

        # Get wanikani levels, assuming all tags are wanikani tags
        for entry in details_json.get('tags', []):
            if not entry.startswith('wanikani'):
                self._log_message(f'Unexpected tag: {entry}')
                continue

            wk_level = int(entry[len('wanikani'):])
            wk_query = details_json["japanese"][0]["word"]  # todo optimize search query
            tags += [EMBED_DETAILS_TAGS_WANIKANI_STEM.format(level=wk_level, query=wk_query)]

        # Default no-tags message
        if not tags:
            tags = [EMBED_DETAILS_TAGS_NONE]

        tags = '\n'.join(tags)

        # Get other forms
        many_forms = len(readings) > 1
        other_forms = '、'.join([self._form_readable(form) for form in readings[1:]])

        # Get attribution data
        sources = [source for source, value in details_json['attribution'].items() if value]

        # Build embed
        embed_dict = {
            'title': EMBED_DETAILS_TITLE_STEM.format(slug=details_json["slug"]),
            'url': EMBED_DETAILS_URL_STEM.format(slug=details_json["slug"]),
            'color': EMBED_COLOR_JISHO,
            'footer': {'text': EMBED_DETAILS_FOOTER_STEM.format(sources=', '.join(sources))},
            'thumbnail': {'url': EMBED_THUMBNAIL_JISHO},
            'fields': [{'name': EMBED_DETAILS_FIELD_WORD_NAME, 'value': word, 'inline': True},
                       {'name': EMBED_DETAILS_FIELD_TAGS_NAME, 'value': tags, 'inline': True},
                       {
                           'name': EMBED_DETAILS_FIELD_DEFINITIONSTRUNC_NAME if definitions_truncated else EMBED_DETAILS_FIELD_DEFINITIONS_NAME,
                           'value': definitions, 'inline': False}]
                      + ([{'name': EMBED_DETAILS_FIELD_OTHERFORMS_NAME, 'value': other_forms,
                           'inline': False}] if many_forms else [])
        }
        return discord.Embed.from_dict(embed_dict)

    @commands.command(name=COMMAND_LINK, aliases=[COMMAND_LINK_ALIAS], help=COMMAND_LINK_DESC_SHORT, description=HELP_DESCRIPTION_STEM.format(command=COMMAND_LINK))
    async def command_link(self, context, link):  # type: (commands.context, str) -> None
        """
        Analyzes a jisho.org link and tries to show details

        :param context: command context
        :param link: link to analyze
        """
        # Check if there is a url to analyze
        if not link:
            raise SyntaxError(ERROR_INCORRECTARGS_STEM.format(syntax=COMMAND_LINK_SYNTAX))

        # Split link into sections, by '/'
        link_split = link.split('/')

        # Find 'jisho.org' in link, discard that and before parts
        for i in range(len(link_split)):
            if LINK_BASE in link_split[i].lower():
                base_index = i
                break
        else:
            raise SyntaxError(ERROR_LINK_NOTJISHO)
        link_split = link_split[base_index + 1:]

        # Make sure there's a /word or /search after jisho.org (not just the homepage)
        if len(link_split) < 2:
            raise SyntaxError(ERROR_LINK_NOQUERY)

        # Handle a search query (jisho.org/search)
        if link_split[0].lower() == LINK_SEARCH:
            # Get search query, make sure it's not a kanji details page
            query = link_split[1]
            if LINK_KANJI in query:
                raise SyntaxError(ERROR_LINK_NOKANJI)

            # Hand over to function to complete search
            await self.command_search(context, query)

        # Display word details (jisho.org/word)
        elif link_split[0].lower() == LINK_DETAILS:
            # Query the API directly by slug, guaranteed (?) one result, hand over to function to complete
            query = LINK_SLUGSEARCH_STEM.format(slug=link_split[1])
            await self.command_details(context, '1', query)

        else:
            raise SyntaxError(ERROR_LINK_NOTYPE)

    # Command functions - utility, other

    @commands.command(name=COMMAND_PING, aliases=[COMMAND_PING_ALIAS], help=COMMAND_PING_DESC_SHORT, description=HELP_DESCRIPTION_STEM.format(command=COMMAND_PING))
    async def command_ping(self, message):  # type: (discord.Message) -> None
        """
        Pings jisho-bot

        :param message: message that requested ping
        """
        await message.channel.send(PING_RESPONSE)

    @commands.command(name=COMMAND_VERSION, aliases=[COMMAND_VERSION_ALIAS], help=COMMAND_VERSION_DESC_SHORT, description=HELP_DESCRIPTION_STEM.format(command=COMMAND_VERSION))
    async def command_version(self, message):  # type: (discord.Message) -> None
        """
        Shows jisho-bot version

        :param message: message that requested version
        """
        await message.channel.send(BOT_VERSION)

    # Not used, conflicts with built-in help
    # def _command_help_embed(self):  # type: () -> discord.Embed
    #     """
    #     Builds a help embed
    #
    #     :return: Help embed
    #     """
    #     # Build embed
    #     embed_dict = {
    #         'title': EMBED_HELP_TITLE,
    #         'color': EMBED_COLOR_BOT,
    #         'footer': {'text': EMBED_HELP_FOOTER},
    #         'fields': [{'name': EMBED_HELP_FIELD_ABOUT_NAME, 'value': EMBED_HELP_FIELD_ABOUT_VALUE,
    #                     'inline': False},
    #                    {'name': EMBED_HELP_FIELD_LOOKUP_NAME, 'value': EMBED_HELP_FIELD_LOOKUP_VALUE,
    #                     'inline': False},
    #                    {'name': EMBED_HELP_FIELD_UTILITY_NAME, 'value': EMBED_HELP_FIELD_UTILITY_VALUE,
    #                     'inline': False}]
    #     }
    #     return discord.Embed.from_dict(embed_dict)

    async def command_unknown(self, message):  # type: (discord.Message) -> None
        """
        Handles an unknown command

        :param message: message with unknown command
        """
        await message.channel.send(UNKNOWN_RESPONSE)

    # Helper methods - wait for reactions

    async def _wait_search(self, message):  # type: (discord.Message) -> None
        """
        Waits for a reaction on a search results embed

        :param message: message to wait for a reaction to
        """
        # Wait for a reaction added to this message, by the original author, that is a valid emoji
        def check(reaction, user):
            results = self._get_results_list(self.cache[message].response)
            return reaction.message == message and user == self.cache[message].author \
                   and str(reaction.emoji) in [REACT_X] + (REACTS_ARROWS if len(results) > RESULTS_PER_PAGE else []) + REACTS_NUMS[:min(RESULTS_PER_PAGE, len(results))]

        # On reaction, handle it appropriately (and clear reactions/cache on timeout)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=TIMEOUT, check=check)
            if str(reaction) == REACT_X:
                await self._action_clear(message)
            elif str(reaction) in REACTS_NUMS:
                await self._action_showdetails(message, REACTS_NUMS.index(str(reaction)))
            elif str(reaction) in REACTS_ARROWS:
                await self._action_changepage(message, reaction, user)
        except asyncio.TimeoutError:
            await message.clear_reactions()
            await self.cache.remove(message)

    async def _wait_details(self, message):  # type: (discord.Message) -> None
        """
        Waits for a reaction on a details embed

        :param message: message to wait for a reaction to
        """
        # Wait for a reaction added to this message, by the original author, that is a valid emoji
        def check(reaction, user):
            return reaction.message == message and user == self.cache[message].author and str(reaction.emoji) in [REACT_RETURN, REACT_X]

        # On reaction, handle it appropriately (and clear reactions/cache on timeout)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=TIMEOUT, check=check)
            if str(reaction) == REACT_X:
                await self._action_clear(message)
            elif str(reaction) == REACT_RETURN:
                await self._action_back(message)
        except asyncio.TimeoutError:
            await message.clear_reactions()
            await self.cache.remove(message)

    async def _wait_nothing(self, message):  # type: (discord.Message) -> None
        """
        Waits for a reaction on an embed that can only be removed

        :param message: message to wait for a reaction to
        """
        # Wait for a reaction added to this message, by the original author, that is a valid emoji
        def check(reaction, user):
            return reaction.message == message and user == self.cache[message].author and str(reaction.emoji) == REACT_X

        # On reaction, handle it appropriately (and clear reactions/cache on timeout)
        try:
            await self.bot.wait_for('reaction_add', timeout=TIMEOUT, check=check)
            await self._action_clear(message)
        except asyncio.TimeoutError:
            await message.clear_reactions()
            await self.cache.remove(message)

    # Helper methods - reaction actions

    async def _action_back(self, message):  # type: (discord.Message) -> None
        """
        Goes back to search results from details

        :param message: message to go back
        """
        # Generate new embed
        messagestate = self.cache[message]
        new_embed = self._command_search_embedfromjson(messagestate.query, messagestate.response, messagestate.offset)

        # Edit message and reactions
        await message.edit(embed=new_embed)
        await self._removereactions_all(message)
        await self._addreactions_search(message, messagestate.response)

        # Wait for user interaction
        await self._wait_search(message)

    async def _action_clear(self, message):
        """
        Removes a message

        :param message: message to remove
        """
        await self.cache.remove(message)
        await message.delete()

    async def _action_showdetails(self, message, number):  # type: (discord.Message, int) -> None
        """
        Shows details for a search result

        :param message: message that had search results
        :param number: search result number to show details for (zero-indexed)
        """
        messagestate = self.cache[message]

        # Ignore invalid indexes
        if number + messagestate.offset >= len(self._get_results_list(messagestate.response)):
            return await self._wait_search(message)

        # Create new details embed
        new_embed = self._command_details_embedfromjson(number + messagestate.offset, messagestate.query, messagestate.response)

        # Edit message and reactions
        await message.edit(embed=new_embed)
        await self._removereactions_all(message)
        await self._addreactions_details(message)

        # Wait for user interaction
        await self._wait_details(message)

    async def _action_changepage(self, message, reaction, user):  # type: (discord.Message, discord.Reaction, discord.User) -> None
        """
        Changes pages on a search results embed

        :param message: message that has search results
        :param reaction: reacted reaction
        :param user: reacting user
        """
        messagestate = self.cache[message]
        delta = (-RESULTS_PER_PAGE, RESULTS_PER_PAGE)[str(reaction) == REACT_ARROW_RIGHT]

        # Ignore page changes that would go out of bounds
        if not 0 <= messagestate.offset + delta < len(messagestate.response['data']):
            return await self._wait_search(message)

        # Create new search embed
        self.cache[message].offset += delta
        new_embed = self._command_search_embedfromjson(messagestate.query, messagestate.response, messagestate.offset)

        # Edit message and reactions
        await message.edit(embed=new_embed)
        await message.remove_reaction(reaction, user)

        # Wait for user interaction
        await self._wait_search(message)

    # Helper methods - add/remove reactions

    async def _addreactions_xonly(self, message):  # type: (discord.Message) -> None
        """
        Adds an x reaction to clear a sent embed

        :param message: Message to add reaction to
        :return: Nothing
        """
        await message.add_reaction(REACT_X)

    async def _addreactions_search(self, message, response_json):  # type: (discord.Message, dict) -> None
        """
        Adds left and right arrows (if needed), numbers (as appropriate), and an x react to a search results message

        :param message: Message to add reactions to
        :param response_json: response json to find what reactions are needed
        :return: Nothing
        """
        results = self._get_results_list(response_json)
        many_pages = len(results) > RESULTS_PER_PAGE

        if many_pages:
            await message.add_reaction(REACT_ARROW_LEFT)

        # Add five number reactions unless there are a fewer number of search results
        for reaction in REACTS_NUMS[:min(RESULTS_PER_PAGE, len(results))]:
            await message.add_reaction(reaction)

        if many_pages:
            await message.add_reaction(REACT_ARROW_RIGHT)

        await message.add_reaction(REACT_X)

    async def _addreactions_details(self, message):  # type: (discord.Message) -> None
        """
        Adds return and x react to a details message

        :param message: Message to add reactions to
        """
        await message.add_reaction(REACT_RETURN)
        await message.add_reaction(REACT_X)

    async def _removereactions_all(self, message):  # type: (discord.Message) -> None
        """
        Removes all reactions from a message

        :param message: Message to remove reactions from
        """
        await message.clear_reactions()

    # Until there are other things to do when removing from cache, this works todo cache is now effectively time-based, is this still needed?
    _cache_cleanup = _removereactions_all

    # Helper methods - logging  todo change to something else other than console / stdout and stderr

    async def _report_error(self, channel, author, error_message):  # type: (discord.TextChannel, discord.User, str) -> None
        """
        Reports an error by sending an embed, as well as printing to stderr

        :param channel: channel to send error report to
        :param author: original author that caused error
        :param error_message: reported error
        :return: Nothing
        """
        self._log_error()

        embed_dict = {
            'title': EMBED_ERROR_TITLE,
            'description': error_message,
            'color': EMBED_COLOR_ERROR,
            'footer': {'text': EMBED_ERROR_FOOTER}
        }

        embed = discord.Embed.from_dict(embed_dict)

        bot_message = await channel.send(embed=embed)
        await bot_message.add_reaction(REACT_X)
        await self.cache.insert(MessageState(author, bot_message, self._cache_cleanup))

    def _log_message(self, message):  # type: (str) -> None
        """
        Logs a message to stdout

        :param message: message to log
        :return: Nothing
        """
        print(message)

    def _log_error(self):  # type: () -> None
        """
        Logs error traceback and message to stderr

        :return: Nothing
        """
        traceback.print_exc(limit=3, file=sys.stderr)

    # Helper methods - other

    async def _api_call(self, query):  # type: (str) -> dict
        """
        Helper method to do jisho.org's API call

        :param query: search query
        :return: JSON response
        :raises ValueError: status code is not 200 OK
        """
        async with self.session.get(API_SEARCH_STEM.format(query=query)) as response:
            status_code = response.status
            response_json = await response.json()

        if status_code != STATUS_OK:
            raise ValueError(ERROR_BADSTATUS_STEM.format(status=status_code))

        return response_json

    def _get_results_list(self, response_json):  # type: (dict) -> list
        """
        Helper method to get the list of search results from the response JSON (in case format changes later)

        :param response_json: response JSON returned from API
        :return: list of responses
        """
        return response_json['data']

    def _get_readings_list(self, details_json):  # type: (dict) -> list
        """
        Helper method to get the list of readings for a search result

        :param details_json: search result JSON
        :return: list of readings (dicts)
        """
        return details_json['japanese']

    def _form_readable(self, form):  # type: (dict) -> str
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


def setup(bot):
    bot.add_cog(JishoCog(bot))

