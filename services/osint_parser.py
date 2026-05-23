import asyncio
import random
import re
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import generativeai as genai
import config

# Initialize Gemini AI
ai_enabled = False
if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        ai_enabled = True
        print("🟢 Gemini AI enabled for OSINT parser.")
    except Exception as e:
        print(f"🔴 Failed to configure Gemini AI for parser: {e}")

# Reusable list of mock local Greek/English leads for Demo Mode
MOCK_LEADS = [
    {
        "author": "Eleni_K",
        "chat": "chalkida_community_chat",
        "text": "Γεια σας κορίτσια! Ψάχνω ένα καλό κομμωτήριο στη Χαλκίδα για ξάνοιγμα και μπαλαγιάζ. Έχει κάνει καμία πρόσφατα; Θέλω προσεκτική δουλειά γιατί η τρίχα μου είναι λεπτή.",
        "lang": "GR"
    },
    {
        "author": "Sophia_Greece",
        "chat": "evia_classifieds",
        "text": "Hello! Can anyone recommend a high-quality hair stylist in Chalkida? I need a modern haircut (bob style) and a solid color correction. Thanks!",
        "lang": "EN"
    },
    {
        "author": "Maria_D",
        "chat": "chalkida_women",
        "text": "Καλησπέρα! Έχετε να προτείνετε κάποιο κομμωτήριο στη Χαλκίδα που να κάνει καλή θεραπεία ενυδάτωσης; Τα μαλλιά μου έχουν καεί από το ντεκαπάζ...",
        "lang": "GR"
    }
]

async def generate_outreach_draft(lead_text: str, lang: str) -> str:
    """
    Generates a personalized response draft using Gemini AI based on the hair studio portfolio.
    If Gemini is disabled, returns a high-quality pre-written template.
    """
    if not ai_enabled:
        # Pre-written templates for home-based/mobile hairdressing services (strictly haircuts)
        if lang == "GR":
            return (
                f"Γεια σας! ✨ Είδαμε ότι ψάχνετε για κομμωτήριο στη Χαλκίδα. \n\n"
                f"Κάνω ποιοτικά κουρέματα που δεν απαιτούν ιδιαίτερο styling, στο σπίти μου στη Χαλκίδα ή με επίσκεψη στο χώρο σας! \n"
                f"👉 Записаться и посмотреть работы можно в боте: @your_bot"
            )
        elif lang in ("RU", "UA"):
            return (
                f"Здравствуйте! ✨ Заметили, что вы ищете парикмахера в Халкиде.\n\n"
                f"Я делаю качественные практичные стрижки, не требующие сложной укладки. Принимаю у себя на дому в Халкиде или могу приехать к вам!\n"
                f"👉 Посмотреть работы и записаться онлайн можно в боте: @your_bot"
            )
        else:
            return (
                f"Hello! ✨ We noticed you are looking for a hair stylist in Chalkida. \n\n"
                f"I offer high-quality, low-maintenance haircuts. Available at my home in Chalkida or with convenient home visits nearby! \n"
                f"👉 Check out my work and book a slot in my Bot: @your_bot"
            )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        system_instructions = (
            "You are a friendly assistant for Anfisa, a professional independent hairdresser in Chalkida, Greece. "
            "She offers services at her home in Chalkida or via home visits nearby. She specializes ONLY in practical, high-quality, low-maintenance haircuts (women's, men's, children's) that do not require complex styling. She does NOT do any hair coloring (dyeing, balayage, highlights, etc.) anymore. "
            "Generate a highly polite, warm, cozy, and converting response to a user looking for a hairdresser/haircut in Chalkida. "
            "Do NOT mention coupons, discounts, or referrals. Show personal warmth, present her home/mobile services, and invite them to check the bot. "
            "Write the response in the exact same language as the user query (Greek, English, Russian, or Ukrainian). "
            "Be concise, natural, and friendly. Do not use hashtags."
        )
        
        prompt = f"{system_instructions}\n\nClient query in local group: {lead_text}\n\nDraft response:"
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"🔴 Gemini generation failed, using fallback template: {e}")
        return await generate_outreach_draft(lead_text, lang)


async def send_lead_card_to_admins(bot: Bot, lead_data: dict):
    """
    Compiles a telemetry JSON card and pushes it to all administrators.
    """
    author = lead_data["author"]
    chat = lead_data["chat"]
    text = lead_data["text"]
    lang = lead_data["lang"]
    
    # Generate response draft
    ai_draft = await generate_outreach_draft(text, lang)
    
    admin_text = (
        f"🚨 *ОБНАРУЖЕН НОВЫЙ ЛИД (OSINT PARSER)* 🔎\n\n"
        f"👥 *Источник:* @{chat}\n"
        f"👤 *Автор:* @{author}\n"
        f"📝 *Сообщение:* \n"
        f"«_{text}_»\n\n"
        f"🤖 *ИИ-Черновик ответа (AI Response Draft):*\n"
        f"```{ai_draft}```\n\n"
        f"💡 _Вы можете скопировать этот ответ и отправить его напрямую клиенту!_"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Написать клиенту", url=f"https://t.me/{author}"))
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            print(f"Failed to send lead alert to admin {admin_id}: {e}")


async def run_telethon_parser(bot: Bot):
    """
    Core Telethon async loop that connects to the Telegram network as a client
    to parse messages in public channels.
    """
    if not config.TELETHON_API_ID or not config.TELETHON_API_HASH:
        print("⚠️ TELETHON_API_ID or TELETHON_API_HASH missing. OSINT Parser disabled.")
        return
        
    try:
        from telethon import TelegramClient, events
        
        print(f"🔎 Starting Telethon client session for OSINT parser (API ID: {config.TELETHON_API_ID})...")
        client = TelegramClient('osint_parser_session', config.TELETHON_API_ID, config.TELETHON_API_HASH)
        
        all_keywords = config.KEYWORDS_GR + config.KEYWORDS_EN + config.KEYWORDS_RU + config.KEYWORDS_UA
        
        @client.on(events.NewMessage)
        async def handler(event):
            if event.is_group or event.is_channel:
                message_text = event.message.message
                if not message_text:
                    return
                
                message_text_lower = message_text.lower()
                matched = any(kw.lower() in message_text_lower for kw in all_keywords)
                if matched:
                    sender = await event.get_sender()
                    sender_username = getattr(sender, 'username', None)
                    if not sender_username:
                        return
                        
                    chat = await event.get_chat()
                    chat_username = getattr(chat, 'username', 'chat_group')
                    
                    # Detect language based on character ranges
                    is_greek = any(913 <= ord(c) <= 937 or 945 <= ord(c) <= 969 for c in message_text)
                    is_cyrillic = any(1024 <= ord(c) <= 1279 for c in message_text)
                    
                    if is_greek:
                        lang = "GR"
                    elif is_cyrillic:
                        lang = "RU"
                    else:
                        lang = "EN"
                    
                    lead_data = {
                        "author": sender_username,
                        "chat": chat_username,
                        "text": message_text,
                        "lang": lang
                    }
                    
                    await send_lead_card_to_admins(bot, lead_data)
                    
        await client.start()
        print("🟢 Telethon OSINT parser connected and actively listening to monitored spaces!")
        await client.run_until_disconnected()
        
    except ImportError:
        print("⚠️ Telethon package not fully installed or failed to import. OSINT Parser disabled.")
    except Exception as e:
        print(f"🔴 Telethon parser error: {e}. OSINT Parser disabled.")


async def run_demo_simulation(bot: Bot):
    """
    Simulation loop that generates mock local leads in Chalkida periodically.
    """
    print("📢 OSINT Simulator is active. Will generate mock Chalkida leads every 60 seconds.")
    
    await asyncio.sleep(15)
    
    while True:
        try:
            if not config.ADMIN_IDS:
                await asyncio.sleep(30)
                continue
                
            lead = random.choice(MOCK_LEADS)
            await send_lead_card_to_admins(bot, lead)
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            print("🛑 OSINT Simulator stopped.")
            break
        except Exception as e:
            print(f"🔴 OSINT Simulator error: {e}")
            await asyncio.sleep(60)
