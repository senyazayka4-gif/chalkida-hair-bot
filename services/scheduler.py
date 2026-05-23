from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import os

scheduler = AsyncIOScheduler()

async def send_reminder_message(bot: Bot, chat_id: int, text: str):
    """
    Helper function to send the reminder message to the client.
    """
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        print(f"🔔 Reminder pushed successfully to user {chat_id}.")
    except Exception as e:
        print(f"🔴 Failed to push reminder to {chat_id}: {e}")


def schedule_appointment_reminders(bot: Bot, appointment_id: int, date_str: str, slot_str: str, chat_id: int):
    """
    Schedules two automated reminders (T-24h and T-2h) using APScheduler.
    """
    try:
        # Parse datetime
        # date_str: YYYY-MM-DD, slot_str: HH:MM
        app_datetime = datetime.strptime(f"{date_str} {slot_str}", "%Y-%m-%d %H:%M")
        
        now = datetime.now()
        
        # 1. 24-Hour Reminder
        reminder_24h_time = app_datetime - timedelta(hours=24)
        if reminder_24h_time > now:
            text_24h = (
                f"⏰ *Напоминание о записи!* \n\n"
                f"Завтра в *{slot_str}* у вас запланирован визит в парикмахерскую студию в Халкиде.\n"
                f"Мы очень ждем вас на преображение! ✨"
            )
            scheduler.add_job(
                send_reminder_message,
                trigger="date",
                run_date=reminder_24h_time,
                args=[bot, chat_id, text_24h],
                id=f"rem_24h_{appointment_id}",
                replace_existing=True
            )
            print(f"📅 Reminder scheduled for {reminder_24h_time} (24h before app #{appointment_id}).")
            
        # 2. 2-Hour Reminder
        reminder_2h_time = app_datetime - timedelta(hours=2)
        if reminder_2h_time > now:
            text_2h = (
                f"⚡️ *Ждем вас сегодня!* \n\n"
                f"Напоминаем, что через 2 часа (*в {slot_str}*) ваш визит к нашему мастеру.\n"
                f"🏠 *Адрес:* Chalkida, Evia (центр).\n"
                f"До скорой встречи! 💇‍♀️"
            )
            scheduler.add_job(
                send_reminder_message,
                trigger="date",
                run_date=reminder_2h_time,
                args=[bot, chat_id, text_2h],
                id=f"rem_2h_{appointment_id}",
                replace_existing=True
            )
            print(f"📅 Reminder scheduled for {reminder_2h_time} (2h before app #{appointment_id}).")

    except Exception as e:
        print(f"🔴 Error scheduling reminders: {e}")

def start_scheduler():
    """
    Starts the APScheduler.
    """
    if not scheduler.running:
        scheduler.start()
        print("⏰ APScheduler background worker started successfully.")
