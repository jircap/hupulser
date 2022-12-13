import collections
import numpy as np


class DataBuffer(object):
    def __init__(self, size):
        self._size = size
        self._buffer = collections.deque(np.zeros(self._size))

    @property
    def buffer(self):
        return self._buffer

    def __str__(self):
        items = ['{!r}'.format(item) for item in self._buffer]
        return '[' + ', '.join(items) + ']'

    def update(self, new_data):
        self._buffer.popleft()
        self._buffer.append(new_data)

    def clear(self):
        for i in range(self._size):
            self._buffer.popleft()
            self._buffer.append(0)

    def average_value_from_last_n_values(self, n):
        total = 0
        for i in range(-1, -n - 1, -1):
            total += self._buffer[i]
        avg = total/n
        return avg
