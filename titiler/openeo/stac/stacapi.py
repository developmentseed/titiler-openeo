"""Stac API backend."""

from contextlib import asynccontextmanager
from typing import Dict, List

from attrs import define, field
from fastapi import FastAPI
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from urllib3 import Retry

from ..settings import PySTACSettings
from .base import STACBackend


@define
class stacApiBackend(STACBackend):
    """PySTAC-Client Backend."""

    url: str = field()

    client: Client = field(init=False)

    def get_collections(self, **kwargs) -> List[Dict]:
        """Return List of STAC Collections."""
        collections = [
            collection.to_dict() for collection in self.client.get_collections()
        ]
        return collections

    def get_collection(self, collection_id: str, **kwargs) -> Dict:
        """Return STAC Collection"""
        col = self.client.get_collection(collection_id)
        return col.to_dict()

    def get_items(self, **kwargs) -> List[Dict]:
        """Return List of STAC Items."""
        return []

    def get_lifespan(self):
        """pystac lifespan function."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """init PySTAC Client."""
            settings = PySTACSettings()

            stac_api_io = StacApiIO(
                max_retries=Retry(
                    total=settings.retry,
                    backoff_factor=settings.retry_factor,
                ),
            )

            self.client = Client.open(self.url, stac_io=stac_api_io)
            yield
            self.client = None

        return lifespan