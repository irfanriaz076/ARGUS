from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from backend.config import settings

_driver: Optional[AsyncDriver] = None


async def init_driver() -> AsyncDriver:
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    await _driver.verify_connectivity()
    return _driver


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


def get_driver() -> AsyncDriver:
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised — call init_driver() first")
    return _driver
