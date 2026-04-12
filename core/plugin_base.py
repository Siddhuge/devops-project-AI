from abc import ABC, abstractmethod

class BasePlugin(ABC):

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def parse(self):
        pass