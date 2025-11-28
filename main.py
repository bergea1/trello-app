"""
Trello Automation Engine

This application monitors CUE articles and automatically creates/updates
Trello cards for both online (NETT) and print (PAPIR) publications.

Features:
- Monitors CUE for new articles and creates Trello cards
- Updates existing Trello cards with changes from CUE
"""

import asyncio
import logging
import signal
import sys

from config import Config
from engine import Engine

shutdown_flag = False


def signal_handler(signum, _):
    """Handle shutdown signals"""
    global shutdown_flag
    signal_name = signal.Signals(signum).name
    print(f"\n🛑 Received {signal_name} - Initiating graceful shutdown...")
    logging.info("Shutdown signal received: %s", signal_name)
    shutdown_flag = True


async def interruptible_sleep(seconds: int) -> bool:
    """
    Sleep for specified seconds, checking shutdown_flag every second.
    Returns True if shutdown was requested, False otherwise.
    Provides better code organization by centralizing the sleep pattern.
    """
    for _ in range(seconds):
        if shutdown_flag:
            return True
        await asyncio.sleep(1)
    return False


async def run_nett(engine):
    """Kjører i loop for nett"""
    logging.info("🌐 NETT monitoring started - checking every 60 seconds")

    while not shutdown_flag:
        try:
            logging.info("🔍 NETT: Checking for new articles...")
            await engine.check_for_new("nett")

            if shutdown_flag:
                break

            logging.info("⏱️  NETT: Waiting 60 seconds before checking for changes...")
            if await interruptible_sleep(60):
                break

            if shutdown_flag:
                break

            logging.info("🔄 NETT: Checking for changes in existing cards...")
            await engine.check_for_changes("nett")

        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error("🚨 NETT Connection Error: %s", e)
            logging.info("⏰ Retrying in 60 seconds...")
            if await interruptible_sleep(60):
                break
        except (ValueError, RuntimeError, KeyError) as e:
            logging.error("💥 NETT Unexpected Error: %s", e, exc_info=True)
            logging.info("⏰ Retrying in 60 seconds...")
            if await interruptible_sleep(60):
                break

    logging.info("🌐 NETT monitoring stopped")


async def run_papir(engine):
    """Kjører i loop for papir"""
    logging.info("📰 PAPIR monitoring started - checking every 180 seconds")

    while not shutdown_flag:
        try:
            logging.info("🔍 PAPIR: Checking for new articles...")
            await engine.check_for_new("papir")

            if shutdown_flag:
                break

            logging.info("⏱️  PAPIR: Waiting 180 seconds before checking for changes...")
            if await interruptible_sleep(180):
                break

            if shutdown_flag:
                break

            logging.info("🔄 PAPIR: Checking for changes in existing cards...")
            await engine.check_for_changes("papir")

        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error("🚨 PAPIR Connection Error: %s", e)
            logging.info("⏰ Retrying in 60 seconds...")
            if await interruptible_sleep(60):
                break
        except (ValueError, RuntimeError, KeyError) as e:
            logging.error("💥 PAPIR Unexpected Error: %s", e, exc_info=True)
            logging.info("⏰ Retrying in 60 seconds...")
            if await interruptible_sleep(60):
                break

    logging.info("📰 PAPIR monitoring stopped")


async def main():
    """Main function"""

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    engine = Engine()
    tasks = []

    print("=" * 60)
    print("🚀 TRELLO AUTOMATION ENGINE")
    print("=" * 60)

    app_name = Config.APP_NAME or "Unknown application"
    app_version = Config.APP_VERSION or "Unknown version"
    mode = Config.MODE or "Development"

    print(f"📱 Application: {app_name}")
    print(f"📊 Version: {app_version}")
    print(f"🔧 Mode: {mode.upper()}")
    print("-" * 60)

    print("⚙️  CONFIGURATION STATUS:")
    print("-" * 30)

    if Config.RUN_NETT:
        print("✅ NETT Mode: ENABLED")
        print("   → Monitoring online articles from CUE")
        print("   → Creating/updating Trello cards for web content")
        print("   → Check interval: 60 seconds for new + changes")
    else:
        print("❌ NETT Mode: DISABLED")
        print("   → Online article monitoring is turned off")

    print()

    if Config.RUN_PAPIR:
        print("✅ PAPIR Mode: ENABLED")
        print("   → Monitoring print articles from CUE")
        print("   → Creating/updating Trello cards for print content")
        print("   → Check interval: 180 seconds for new + changes")
    else:
        print("❌ PAPIR Mode: DISABLED")
        print("   → Print article monitoring is turned off")

    print()

    if Config.INCLUDE_CHANGE:
        print("✅ CHANGE TRACKING: ENABLED")
        print("   → Last modified dates will be updated on cards")
    else:
        print("❌ CHANGE TRACKING: DISABLED")
        print("   → Last modified dates will NOT be updated")
    if Config.INCLUDE_GODKJENT_URL:
        print("✅ GODKJENT URL: INCLUDED")
        print("   → 'Godkjent' URLs will be added to Trello cards")
    else:
        print("❌ GODKJENT URL: EXCLUDED")
        print("   → 'Godkjent' URLs will NOT be added to Trello cards")

    if Config.INCLUDE_PUBLISERT_URL:
        print("✅ PUBLISERT URL: INCLUDED")
        print("   → 'Publisert' URLs will be added to Trello cards")
    else:
        print("❌ PUBLISERT URL: EXCLUDED")
        print("   → 'Publisert' URLs will NOT be added to Trello cards")

    print("-" * 60)

    if Config.RUN_NETT:
        tasks.append(run_nett(engine))
        print("📋 Scheduled: NETT monitoring task")

    if Config.RUN_PAPIR:
        tasks.append(run_papir(engine))
        print("📋 Scheduled: PAPIR monitoring task")

    if tasks:
        print(f"\n🎯 Starting {len(tasks)} monitoring task(s)...")
        print("=" * 60)
        print("🔄 ENGINE RUNNING - Press Ctrl+C to stop")
        print("=" * 60)

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logging.info("Tasks cancelled during shutdown")
        finally:
            print("\n" + "=" * 60)
            print("✅ SHUTDOWN COMPLETE")
            print("=" * 60)
    else:
        print("\n⚠️  WARNING: No tasks scheduled!")
        print("💡 SOLUTION: Enable at least one mode by setting:")
        print("   • RUN_NETT=True (for online articles)")
        print("   • RUN_PAPIR=True (for print articles)")
        print("=" * 60)
        logging.warning(
            "No tasks scheduled to run. Check RUN_NETT and RUN_PAPIR config values."
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        sys.exit(0)
    except (RuntimeError, ValueError) as e:
        print(f"\n💥 Fatal error: {e}")
        logging.error("Fatal error in main: %s", e, exc_info=True)
        sys.exit(1)
