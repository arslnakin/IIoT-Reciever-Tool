from PyQt6.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod, ABCMeta

class QObjectABCMeta(type(QObject), ABCMeta):
    pass

class ProtocolHandlerBase(QObject, ABC, metaclass=QObjectABCMeta):
    log_message = pyqtSignal(str)

    def __init__(self, ui):
        super().__init__()
        self.ui = ui

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_status(self) -> str:
        pass

    @abstractmethod
    def serialize(self) -> dict:
        pass

    @abstractmethod
    def deserialize(self, data: dict):
        pass