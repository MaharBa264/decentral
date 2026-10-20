"""Boundary for future source-system adapters. No integration is included in H0."""
from abc import ABCMeta, abstractmethod


class CatalogExtractor(object, metaclass=ABCMeta):
    """Adapters transform an external capture into a schema-valid snapshot.

    Implementations must receive an explicit local input path or in-memory payload;
    they must never commit, transmit, or log the raw capture.
    """
    @abstractmethod
    def to_snapshot(self, capture):
        """Return a decentral.catalog/v1 dictionary; no persistence implied."""
        raise NotImplementedError
