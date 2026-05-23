from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.connection import get_db
from database.models import Appointment, User, MonitoredChannel
from datetime import datetime
import config

router = Router(name="admin")

class AdminStates(StatesGroup):
    add_channel = State()
    block_date = State()
    block_slot = State()

@router.callback_query(F.data.startswith("adm_appr:"))
async def approve_appointment(callback: CallbackQuery, bot: Bot):
    """
    Approves pending appointment. Updates status and alerts client.
    """
    await callback.answer()
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app:
            await callback.message.edit_text("⚠️ Ошибка: запись не найдена.")
            return
            
        if app.status == "approved":
            await callback.message.edit_text("🟢 Эта запись уже была одобрена ранее.")
            return

        app.status = "approved"
        client_id = app.user_id
        client_name = app.user.fullname
        date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m.%Y")
        slot_str = app.slot
        session.commit()

    # Alert Client
    try:
        builder = InlineKeyboardBuilder()
        admin_username = callback.from_user.username or "arsikas"
        builder.row(InlineKeyboardButton(text="💬 Написать мастеру в ЛС", url=f"https://t.me/{admin_username}"))
        
        await bot.send_message(
            chat_id=client_id,
            text=f"🎉 *Ура! Мастер подтвердил вашу запись!* 💇‍♀️\n\n"
                 f"📅 *Дата:* {date_formatted}\n"
                 f"⏰ *Время:* {slot_str}\n"
                 f"📍 *Локация:* Халкида (центр)\n\n"
                 f"Мы ждем вас вовремя. Если ваши планы изменятся, пожалуйста, предупредите нас заранее! ✨",
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        print(f"Failed to alert client {client_id}: {e}")

    await callback.message.edit_text(
        f"✅ *Запись #{app_id} успешно одобрена!*\n"
        f"Клиент {client_name} получил уведомление в чат.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_rej:"))
async def reject_appointment(callback: CallbackQuery, bot: Bot):
    """
    Rejects/cancels pending appointment.
    """
    await callback.answer()
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app:
            await callback.message.edit_text("⚠️ Ошибка: запись не найдена.")
            return

        app.status = "cancelled"
        client_id = app.user_id
        client_name = app.user.fullname
        date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m.%Y")
        slot_str = app.slot
        session.commit()

    # Alert Client
    try:
        await bot.send_message(
            chat_id=client_id,
            text=f"😔 *К сожалению, мастер отклонил вашу запись на {date_formatted} в {slot_str}*.\n\n"
                 f"Возможно, это время занято оффлайн-клиентами. Пожалуйста, откройте меню и "
                 f"выберите другое свободное время в онлайн-календаре!",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to alert client {client_id}: {e}")

    await callback.message.edit_text(
        f"❌ *Запись #{app_id} отклонена*.\n"
        f"Клиент {client_name} уведомлен об отмене.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_view_bookings")
async def admin_view_bookings(callback: CallbackQuery):
    """
    Lists approved and pending bookings for the Admin as clickable buttons.
    """
    await callback.answer()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    builder = InlineKeyboardBuilder()
    
    with get_db() as session:
        bookings = session.query(Appointment).filter(
            Appointment.date >= today_str,
            Appointment.status.in_(["approved", "pending"])
        ).order_by(Appointment.date, Appointment.slot).all()

        if len(bookings) == 0:
            bookings_text = "📅 <b>Список предстоящих записей пуст.</b>\n\nВсе свободные часы открыты для онлайн-записи!"
        else:
            bookings_text = (
                "📅 <b>Предстоящие записи в салон:</b>\n\n"
                "Выберите конкретную запись ниже, чтобы посмотреть детальную анкету клиента, "
                "его фото и иметь возможность отменить/удалить запись:"
            )
            for app in bookings:
                date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m")
                status_emoji = "🟢" if app.status == "approved" else "🟡"
                btn_text = f"{status_emoji} {date_formatted} {app.slot} | {app.user.fullname}"
                builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"adm_view_app:{app.id}"))
            
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        bookings_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

# --- Dynamic Slot Blocking System ---

@router.callback_query(F.data == "admin_block_time")
async def block_time_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminStates.block_date)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        "🔒 <b>Блокировка рабочих часов (Мастер-календарь)</b>\n\n"
        "Вы можете закрыть любой временной слот для онлайн-записи.\n\n"
        "✏️ <b>Введите дату в формате ДД.ММ.ГГГГ (например: 25.05.2026):</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router.message(AdminStates.block_date)
async def block_time_date(message: Message, state: FSMContext):
    date_input = message.text.strip()
    try:
        parsed_date = datetime.strptime(date_input, "%d.%m.%Y")
        db_date_str = parsed_date.strftime("%Y-%m-%d")
        await state.update_data(block_date=db_date_str)
        
        builder = InlineKeyboardBuilder()
        for slot in ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]:
            builder.row(InlineKeyboardButton(text=f"🚫 Заблокировать {slot}", callback_data=f"block_slot:{slot}"))
            
        builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"))
        
        await message.reply(
            f"📅 *Выбранная дата:* {date_input}\n\n"
            f"Выберите слот времени, который хотите закрыть для записи:",
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
        await state.set_state(AdminStates.block_slot)
    except ValueError:
        await message.reply("⚠️ Неверный формат даты. Попробуйте еще раз в формате ДД.ММ.ГГГГ:")

@router.callback_query(AdminStates.block_slot, F.data.startswith("block_slot:"))
async def block_time_slot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    slot = callback.data.split(":")[1]
    data = await state.get_data()
    db_date = data.get("block_date")
    
    with get_db() as session:
        blocked_app = Appointment(
            user_id=callback.from_user.id,
            date=db_date,
            slot=slot,
            status="approved",
            desired_result="🔒 ЗАБЛОКИРОВАНО АДМИНИСТРАТОРОМ"
        )
        session.add(blocked_app)
        session.commit()

    date_formatted = datetime.strptime(db_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    await callback.message.edit_text(
        f"🔒 *Слот {slot} на {date_formatted} успешно заблокирован!* \n\n"
        f"Клиенты больше не увидят это время свободным в календаре.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")).as_markup()
    )
    await state.clear()

# --- OSINT Parser Admin Dashboard ---

@router.callback_query(F.data == "admin_osint")
async def show_admin_osint(callback: CallbackQuery):
    await callback.answer()
    
    with get_db() as session:
        channels = session.query(MonitoredChannel).filter(MonitoredChannel.is_active == True).all()

        channels_list = ""
        if len(channels) == 0:
            channels_list = "🔎 <b>Нет активно сканируемых чатов. Парсер работает в Демо-режиме.</b>"
        else:
            channels_list = "🔎 <b>Активно сканируемые локальные чаты:</b>\n\n"
            for ch in channels:
                title_escaped = (ch.title or 'группа').replace("<", "&lt;").replace(">", "&gt;")
                channels_list += f"• @{ch.channel_username} ({title_escaped})\n"

        osint_text = (
            f"📢 <b>Управление OSINT-парсером лидов</b> 🔍\n\n"
            f"Бот непрерывно сканирует указанные ниже чаты Халкиды на наличие слов: "
            f"<i>hairdresser, κομμωτήριο, κούρεμα, Χαλκίδα, Evia</i>\n\n"
            f"{channels_list}\n\n"
            f"💡 <i>В Демо-режиме бот будет генерировать лиды сам, чтобы вы могли протестировать систему.</i>"
        )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить чат", callback_data="admin_add_channel"))
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        osint_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminStates.add_channel)
    await callback.message.edit_text(
        "📝 <b>Добавление нового локального чата для сканирования:</b>\n\n"
        "Отправьте юзернейм чата без собачки (например: <code>chalkida_market</code>) или ссылку на него:",
        parse_mode="HTML"
    )

@router.message(AdminStates.add_channel)
async def admin_add_channel_finish(message: Message, state: FSMContext):
    raw_input = message.text.strip()
    
    # Safely extract username from full t.me links or @ handles
    if "t.me/" in raw_input:
        channel_user = raw_input.split("t.me/")[-1]
    else:
        channel_user = raw_input
        
    channel_user = channel_user.replace("@", "").strip()
    
    with get_db() as session:
        exists = session.query(MonitoredChannel).filter(MonitoredChannel.channel_username == channel_user).first()
        if exists:
            exists.is_active = True
        else:
            new_ch = MonitoredChannel(
                channel_username=channel_user,
                title=f"Локальный чат {channel_user}",
                is_active=True
            )
            session.add(new_ch)
        session.commit()

    await message.reply(
        f"✅ <b>Чат @{channel_user} успешно добавлен в список мониторинга!</b> \n\n"
        f"Парсер начнет сканирование сообщений при следующем перезапуске бота.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")).as_markup()
    )
    await state.clear()


# --- New Detailed Booking Card & Deletion/Cancellation Handlers ---

@router.callback_query(F.data.startswith("adm_view_app:"))
async def admin_view_specific_appointment(callback: CallbackQuery):
    """
    Renders a super-detailed client card with all questionnaire answers and action buttons.
    """
    await callback.answer()
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app:
            await callback.message.edit_text(
                "⚠️ Ошибка: запись не найдена.",
                reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_view_bookings")).as_markup()
            )
            return
            
        parsed_date = datetime.strptime(app.date, "%Y-%m-%d")
        date_formatted = parsed_date.strftime("%d.%m.%Y")
        status_text = "🟢 Одобрена" if app.status == "approved" else "🟡 В ожидании подтверждения"
        
        card = (
            f"📅 <b>ДЕТАЛИ ЗАПИСИ #{app.id}</b>\n\n"
            f"📌 <b>Статус:</b> {status_text}\n"
            f"📆 <b>Дата и время:</b> {date_formatted} в {app.slot}\n\n"
            f"👤 <b>КЛИЕНТ:</b>\n"
            f"• <b>Имя:</b> {app.user.fullname or 'Не указано'}\n"
            f"• <b>Telegram:</b> @{app.user.username or 'нет'}\n"
            f"• <b>ID пользователя:</b> <code>{app.user_id}</code>\n\n"
            f"📋 <b>АНКЕТА КЛИЕНТА:</b>\n"
            f"• <b>Тип/длина волос:</b> {app.hair_length or 'Не указано'}\n"
            f"• <b>Пожелания:</b> <i>{app.desired_result or 'Без комментариев'}</i>\n"
        )
        
        builder = InlineKeyboardBuilder()
        
        # Link to open Telegram private chat with client
        if app.user.username:
            builder.row(InlineKeyboardButton(text="💬 Написать клиенту в ЛС", url=f"https://t.me/{app.user.username}"))
            
        # Button to view attached hair photo if exists
        if app.photo_path:
            builder.row(InlineKeyboardButton(text="📷 Посмотреть фото волос", callback_data=f"adm_show_photo:{app.id}"))
            
        # Action Buttons
        if app.status == "pending":
            builder.row(
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_appr_detail:{app.id}"),
                InlineKeyboardButton(text="🗑️ Отменить/Удалить", callback_data=f"adm_del_detail:{app.id}")
            )
        else:
            builder.row(InlineKeyboardButton(text="🗑️ Отменить/Удалить запись", callback_data=f"adm_del_detail:{app.id}"))
            
        builder.row(InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_view_bookings"))
        
        await callback.message.edit_text(
            card,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data.startswith("adm_show_photo:"))
async def admin_show_appointment_photo(callback: CallbackQuery, bot: Bot):
    """
    Sends the uploaded client photo to the admin chat.
    """
    await callback.answer("Отправляю фото...")
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app or not app.photo_path:
            await callback.message.reply("⚠️ Фото не найдено к этой записи.")
            return
            
        try:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=app.photo_path,
                caption=f"📷 Фото волос клиента к записи #{app_id}"
            )
        except Exception as e:
            await callback.message.reply(f"⚠️ Не удалось загрузить фото: {e}")

@router.callback_query(F.data.startswith("adm_appr_detail:"))
async def admin_approve_detail(callback: CallbackQuery, bot: Bot):
    """
    Approves pending appointment from detailed view, alerts client, and updates card.
    """
    await callback.answer("Запись одобрена!")
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app:
            await callback.message.edit_text("⚠️ Ошибка: запись не найдена.")
            return
            
        app.status = "approved"
        client_id = app.user_id
        date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m.%Y")
        slot_str = app.slot
        session.commit()
        
    try:
        builder = InlineKeyboardBuilder()
        admin_username = callback.from_user.username or "arsikas"
        builder.row(InlineKeyboardButton(text="💬 Написать мастеру в ЛС", url=f"https://t.me/{admin_username}"))
        
        await bot.send_message(
            chat_id=client_id,
            text=f"🎉 *Ура! Мастер подтвердил вашу запись!* 💇‍♀️\n\n"
                 f"📅 *Дата:* {date_formatted}\n"
                 f"⏰ *Время:* {slot_str}\n"
                 f"📍 *Локация:* Халкида (центр)\n\n"
                 f"Мы ждем вас вовремя. Если ваши планы изменятся, пожалуйста, предупредите нас заранее! ✨",
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        print(f"Failed to alert client {client_id}: {e}")
        
    # Redirect back to the updated detailed view
    callback.data = f"adm_view_app:{app_id}"
    await admin_view_specific_appointment(callback)

@router.callback_query(F.data.startswith("adm_del_detail:"))
async def admin_delete_detail(callback: CallbackQuery, bot: Bot):
    """
    Cancels/Deletes appointment from detailed view and alerts client.
    """
    await callback.answer("Запись отменена/удалена!")
    app_id = int(callback.data.split(":")[1])
    
    with get_db() as session:
        app = session.query(Appointment).filter(Appointment.id == app_id).first()
        if not app:
            await callback.message.edit_text("⚠️ Ошибка: запись не найдена.")
            return
            
        app.status = "cancelled"
        client_id = app.user_id
        date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m.%Y")
        slot_str = app.slot
        session.commit()
        
    try:
        await bot.send_message(
            chat_id=client_id,
            text=f"😔 *К сожалению, ваша запись на {date_formatted} в {slot_str} была отменена мастером*.\n\n"
                 f"Возможно, изменились рабочие часы или возникли непредвиденные обстоятельства. "
                 f"Пожалуйста, выберите другое свободное время в онлайн-календаре через меню!",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to alert client {client_id}: {e}")
        
    # Show successful deletion notification to admin
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Вернуться к списку", callback_data="admin_view_bookings"))
    
    await callback.message.edit_text(
        f"🗑️ <b>Запись #{app_id} успешно отменена и удалена из календаря!</b>\n"
        f"Клиент получил уведомление об отмене записи.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
