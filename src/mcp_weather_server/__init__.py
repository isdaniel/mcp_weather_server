from .server import main as async_main
import asyncio

def main():
    """Synchronous entry point for the package."""
    asyncio.run(async_main())

__all__ = ['main', 'async_main']
