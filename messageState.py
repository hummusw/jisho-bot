import discord


class Node:
    def __init__(self, value):
        self.value: MessageState = value
        self.next: Node = None


class MessageState:
    def __init__(self, author, query, response, message, offset):
        self.author: discord.User = author
        self.query: str = query
        self.response: dict = response
        self.message: discord.Message = message
        self.offset = offset


class MessageCache:
    def __init__(self, maxsize):  # type: (int) -> None
        self.maxsize: int = maxsize
        self.head: Node = None
        self.size: int = 0

    def insert(self, messagestate):

        # Should be safe for self.head == None
        newnode = Node(messagestate)
        newnode.next = self.head
        self.head = newnode
        self.size += 1

        # Eviction check
        while self.size > self.maxsize:
            self._evict()

    def _evict(self):
        # Can't evict on empty list
        if not self.head:
            return

        # Evict only element
        if self.size == 1:
            # todo remove reactions

            self.head = None

        # Evict element at end
        else:
            prev = None
            curr = self.head

            for i in range(self.size - 1):
                prev, curr = curr, curr.next

            # todo remove reactions

            prev.next = None

    def __getattr__(self, item):  # type: (discord.Message) -> MessageState
        prev = None
        curr = self.head

        while curr and not curr.value.message == item:
            prev, curr = curr, curr.next

        if not curr:
            raise KeyError
        else:
            prev.next = curr.next
            curr.next = self.head
            self.head = curr
            return curr.value

    def remove(self, message):
        if not self.head:
            raise RuntimeError
        # todo left off here

class MessageCacheNaive:
    def __init__(self):
        self.cache = {}

    def __getitem__(self, item):
        return self.cache[item]

    def insert(self, messagestate):  # type: (MessageState) -> None
        self.cache[messagestate.message] = messagestate

    def remove(self, message):
        self.cache.pop(message)