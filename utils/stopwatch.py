import time


class Stopwatch:
    def __init__(self):
        self.start = time.time()

    def reset(self):
        record = time.time() - self.start
        self.start = time.time()
        return record
