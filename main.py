"""Main file for the Ringblad engine"""

import asyncio
import logging

from engine import Engine


async def run_nett(engine):
    """Kjører i loop for nettutgaven"""
    while True:
        try:
            await engine.check_for_new("nett")
            await asyncio.sleep(60)
            await engine.check_for_changes("nett")
        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error("Error: %s", e)
            await asyncio.sleep(60)


async def run_papir(engine):
    """Kjører i loop for papirutgaven"""
    while True:
        try:
            await engine.check_for_new("papir")
            await asyncio.sleep(180)
            await engine.check_for_changes("papir")
        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error("Error: %s", e)
            await asyncio.sleep(60)


async def main():
    """Main function"""
    engine = Engine()
    await asyncio.gather(run_nett(engine), run_papir(engine))


if __name__ == "__main__":
    asyncio.run(main())
