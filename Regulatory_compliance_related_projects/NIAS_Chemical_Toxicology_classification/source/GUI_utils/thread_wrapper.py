from PySide6.QtCore import QThread


class Thread(QThread):
    # kept for compatibility if you want to run arbitrary functions later
    def __init__(self, fn, args, kwargs, parent=None):
        super(Thread, self).__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        self._fn(*self._args, **self._kwargs)
