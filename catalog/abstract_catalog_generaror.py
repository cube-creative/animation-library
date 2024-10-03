

from abc import abstractmethod


class AbstractCatalogGenerator():
    @abstractmethod
    def generate_entry_path(self)->str:
        """ Generate a path for a new entry
        """
        raise NotImplementedError()