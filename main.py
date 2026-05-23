import sys
# Force UTF-8 encoding for standard output on Windows to support printing emojis without crash
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.connection import init_db
from handlers import all_routers
from services.scheduler import start_scheduler
from services.osint_parser import run_telethon_parser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

async def on_startup(bot: Bot):
    """
    Actions performed upon bot startup.
    """
    logger.info("Initializing database schemas...")
    init_db()
    
    logger.info("Starting scheduler services...")
    start_scheduler()
    
    logger.info("Spawning OSINT Lead Parser background worker...")
    asyncio.create_task(run_telethon_parser(bot))
    
    # Notify admins about startup in the background to prevent blocking
    async def notify_admins():
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text="🚀 *Бот Студии Парикмахерского Искусства (Халкида) успешно запущен!*\n\n"
                         "🟢 База данных подключена.\n"
                         "⏰ Шедулер напоминаний активен.\n"
                         "🔎 OSINT-парсер лидов запущен в фоновом режиме.\n\n"
                         "Используйте команду /start для открытия меню.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not send startup message to admin {admin_id}: {e}")

    asyncio.create_task(notify_admins())

def start_dummy_web_server():
    """
    Starts a dummy HTTP server on port 7860 for Hugging Face Spaces health checks.
    """
    import threading
    from http.server import SimpleHTTPRequestHandler, HTTPServer

    class HealthCheckHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            # Always return 200 OK for any paths/query strings to pass Hugging Face health checks
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Chalkida Hair Bot is Running!</h1></body></html>")

    def run_server():
        try:
            server = HTTPServer(("0.0.0.0", 7860), HealthCheckHandler)
            logger.info("🟢 Health check HTTP server started on port 7860.")
            server.serve_forever()
        except Exception as e:
            logger.error(f"🔴 Health check server failed: {e}")

    threading.Thread(target=run_server, daemon=True).start()


async def main():
    # Start dummy web server for HF Spaces
    start_dummy_web_server()
    
    # Check bot token
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("🔴 BOT_TOKEN is missing or is set to placeholder in .env! Bot cannot start.")
        print("\n🛑 ВНИМАНИЕ: Пожалуйста, откройте файл .env и впишите ваш BOT_TOKEN от @BotFather перед запуском!\n")
        sys.exit(1)
        
    # Initialize Bot and Dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    
    # Using memory storage for FSM states
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register all handlers routers
    for router in all_routers:
        dp.include_router(router)
        logger.info(f"Registered router: {router.name}")
        
    # Register startup callback
    dp.startup.register(on_startup)
    
    # Start polling with automatic reconnects
    logger.info("🤖 Zenith Chalkida Hair Bot starting long polling loop...")
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except Exception as e:
                logger.error(f"🔴 Telegram connection error: {e}. Retrying in 10 seconds...")
                await asyncio.sleep(10)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
