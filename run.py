import asyncio
from rich.logging import RichHandler
import logging

from reaktion.run import main

logging.basicConfig(level="INFO", handlers=[RichHandler()])


asyncio.run(main())
