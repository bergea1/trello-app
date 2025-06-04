"""
Hovedfil for programmet.
"""

import asyncio
import logging

from config import Config
from engine import Engine


class EngineRunner:
    """
    Sørger for å kjøre app med riktig tidsintervall.
    """

    def __init__(self, engine):
        self.engine = engine
        self.next_run = {
            "new": asyncio.get_event_loop().time(),
            "nett": asyncio.get_event_loop().time(),
            "papir": asyncio.get_event_loop().time(),
        }

    async def run(self):
        """
        Kjører i intervaller.
        """

        while True:
            now = asyncio.get_event_loop().time()

            try:
                tasks = []
                tasks.extend(await self._schedule_tasks(now))

                if tasks:
                    await asyncio.gather(*tasks)

                await asyncio.sleep(1)

            except (asyncio.CancelledError, AttributeError, RuntimeError) as e:
                logging.error("Unhandled error in engine: %s — retrying in 1m", e)
                await asyncio.sleep(60)

    async def _schedule_tasks(self, now):
        """
        Tidsstyrer hvilke oppgaver som skal kjøres.
        """

        tasks = []

        if now >= self.next_run["new"]:
            tasks.extend(await self._run_task("new"))

        if now >= self.next_run["nett"]:
            tasks.extend(await self._run_task("nett"))

        if now >= self.next_run["papir"]:
            tasks.extend(await self._run_task("papir"))

        return tasks

    async def _run_task(self, task_type):
        """
        Utfører en oppgave utifra type.
        """

        task_map = {
            "new": self._check_new,
            "nett": self._check_changes,
            "papir": self._check_changes,
        }

        if task_type == "new":
            tasks = [
                self.engine.check_new("nett"),
                self.engine.check_new("papir"),
            ]
            self.next_run["new"] = (
                asyncio.get_event_loop().time() + Config.INTERVALS["new"]
            )
        else:
            tasks = [task_map[task_type](task_type)]
            self.next_run[task_type] = (
                asyncio.get_event_loop().time() + Config.INTERVALS[task_type]
            )

        return tasks

    async def _check_new(self, mode):
        """
        Hjelpefunksjon for å sette i gang sjekk etter nye artikler.
        """

        logging.info("Ser etter nye artikler: %s", mode)
        return await self.engine.check_new(mode)

    async def _check_changes(self, mode):
        """
        Hjelpefunksjon for å sette i gang sjekk etter endringer.
        """

        logging.info("Sjekker etter endringer i Cue: %s", mode)
        return await self.engine.check_changes(mode)


async def main():
    """
    Hovedfunksjon for å starte appen.
    """

    logging.info("Starter appen...")
    engine = Engine()
    runner = EngineRunner(engine)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
