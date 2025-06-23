"""Main file for the Ringblad engine"""

import asyncio
import logging

from config import Config
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
    tasks = []

    print(f"Starting {Config.INIT_CONF.get('APP_NAME')}")
    print(f"Version: {Config.INIT_CONF.get('APP_VERSION')}")
    print(f"{Config.INIT_CONF.get('MODE')} mode.")

    if Config.INIT_CONF.get("RUN_NETT"):
        tasks.append(run_nett(engine))
    if Config.INIT_CONF.get("RUN_PAPIR"):
        tasks.append(run_papir(engine))

    if tasks:
        await asyncio.gather(*tasks)
    else:
        logging.warning(
            "No tasks scheduled to run. Check RUN_NETT and RUN_PAPIR config values."
        )


if __name__ == "__main__":
    asyncio.run(main())
