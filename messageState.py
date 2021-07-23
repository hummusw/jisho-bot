from typing import Callable

import discord


class Node:
    """
    Represents a node in a linked list
    """
    def __init__(self, value):
        self.value: MessageState = value
        self.next: Node = None


class MessageState:
    """
    Holds information about a jisho-bot query
    """
    def __init__(self, author, query, response, message, offset, callback):
        self.author: discord.User = author
        self.query: str = query
        self.response: dict = response
        self.message: discord.Message = message
        self.offset: int = offset
        self.callback: Callable = callback

    def __str__(self):
        return f'Message State: author={self.author}, query={self.query}, response={self.response}, message={self.message}, offset={self.offset}, callback={self.callback}'

    __repr__ = __str__


class MessageCache:
    """
    Holds message states in a LRU cache implemented with a linked list
    """

    __KEYERROR_MESSAGE = 'Message not found in cache'

    def __init__(self, maxsize):  # type: (int) -> None
        self.maxsize: int = maxsize
        self.head: Node = None
        self.size: int = 0

    async def insert(self, messagestate):  # type: (MessageState) -> None
        """
        Inserts a new message state at the head of the cache, evicts as necessary

        :param messagestate: message state to add to cache
        :return: nothing
        """
        # Insert at front (safe for empty cache)
        newnode = Node(messagestate)
        newnode.next = self.head
        self.head = newnode
        self.size += 1

        # Eviction check
        while self.size > self.maxsize:
            await self._evict()

    async def _evict(self):  # type: () -> None
        """
        Helper method to evict least recently used message state, calling callback with message as parameter on eviction

        :return: nothing
        """
        # Can't evict on empty list
        if not self.head:
            return

        # Evict only element
        if self.size == 1:
            await self.head.value.callback(self.head.value.message)

            self.head = None
            self.size -= 1

        # Evict element at end
        else:
            prev = None
            curr = self.head

            for i in range(self.size - 1):
                prev, curr = curr, curr.next

            await curr.value.callback(curr.value.message)

            prev.next = None
            self.size -= 1

    def __getitem__(self, item):  # type: (discord.Message) -> MessageState
        """
        Finds a message state by using the message as the key

        :param item: discord message to look for
        :return: message state corresponding to input message
        :raises KeyError: message not found in cache
        """
        # If cache is empty, raise error
        if not self.head:
            raise KeyError(MessageCache.__KEYERROR_MESSAGE)

        # If message is found at head, no need for rearranging
        elif self.head.value.message == item:
            return self.head.value

        # Search rest of cache, if it exists
        else:
            prev = self.head
            curr = prev.next

            # Loop through linked list until end of list or message found
            while curr and not curr.value.message == item:
                prev, curr = curr, curr.next

            # Raise KeyError if not found
            if not curr:
                raise KeyError(MessageCache.__KEYERROR_MESSAGE)

            # Move found node to front of list
            prev.next = curr.next
            curr.next = self.head
            self.head = curr

            return curr.value

    async def remove(self, message):  # type: (discord.Message) -> None
        """
        Removes a message state from the cache using the message as the key, does not call callback

        :param message: message state's message to remove
        :return: nothing
        :raises KeyError: message not found in cache
        """
        # Move message to remove to head
        self[message]

        # Remove head
        self.head = self.head.next
        self.size -= 1

    def print_status(self):
        print(f'Message Cache: {self.size} items stored out of a max of {self.maxsize}')
        i = 0
        curr = self.head
        while curr:
            print(f'[{i}]: {curr.value}')
            i += 1
            curr = curr.next


# class MessageCacheNaive:
#     def __init__(self):
#         self.cache = {}
#
#     def __getitem__(self, item):
#         return self.cache[item]
#
#     def insert(self, messagestate):  # type: (MessageState) -> None
#         self.cache[messagestate.message] = messagestate
#
#     def remove(self, message):
#         self.cache.pop(message)
