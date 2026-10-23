from abc import ABC, abstractmethod

class BaseDomainImporter(ABC):
    domain: str = ""
    name: str = ""

    def is_supported(self) -> bool:
        return True

    @abstractmethod
    def search_or_browse(self, query: str = None, page: int = 1, force_refresh: bool = False) -> dict:
        pass
