# coding=utf-8
import threading

class ResettableTimer(threading.Thread):
    def __init__(self, interval, function, args=None, kwargs=None, on_reset=None, on_cancelled=None):
        threading.Thread.__init__(self)
        self._event = threading.Event()
        self._mutex = threading.Lock()
        self.is_reset = True

        if args is None:
            args = []
        if kwargs is None:
            kwargs = dict()

        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.on_cancelled = on_cancelled
        self.on_reset = on_reset

    def run(self):
        while self.is_reset:
            with self._mutex:
                self.is_reset = False
            self._event.wait(self.interval)

        if not self._event.isSet():
            self.function(*self.args, **self.kwargs)
        with self._mutex:
            self._event.set()

    def cancel(self):
        with self._mutex:
            self._event.set()

        if callable(self.on_cancelled):
            self.on_cancelled()

    def reset(self, interval=None):
        with self._mutex:
            if interval:
                self.interval = interval

            self.is_reset = True
            self._event.set()
            self._event.clear()

        if callable(self.on_reset):
            self.on_reset()
