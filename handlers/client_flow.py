import json
import html
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.connection import get_db
from database.models import User, Appointment
import services.calendar_api as calendar_api
import config
from datetime import datetime

router = Router(name="client_flow")

@router.callback_query(F.data == "client_portfolio")
async def show_portfolio(callback: CallbackQuery):
    """
    Renders hairstyle portfolio catalog with inline booking buttons.
    """
    await callback.answer()
    
    portfolio_intro = (
        "🖼️ *НАШЕ ПОРТФОЛИО СТРИЖЕК (вид сзади)*\n\n"
        "👇 Выберите понравившийся стиль стрижки, чтобы записаться к мастеру:"
    )
    
    await callback.message.answer(portfolio_intro, parse_mode="Markdown")
    
    for item in config.PORTFOLIO_ITEMS:
        item_text = (
            f"🌟 *{item['title']}*\n\n"
            f"📝 *Описание:* {item['description']}\n"
            f"⏱️ *Время:* {item['duration']}\n"
            f"💳 *Стоимость:* {item['price']}\n"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📅 Записаться на эту услугу", callback_data="client_book"))
        
        try:
            await callback.message.answer_photo(
                photo=item["photo"],
                caption=item_text,
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )
        except Exception:
            await callback.message.answer(
                item_text,
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )
            
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu"))
    await callback.message.answer(
        "✨ Хотите вернуться в меню?",
        reply_markup=builder.as_markup()
    )

# --- Dynamic Calendar Navigation Handlers ---

@router.callback_query(F.data.startswith("cal:nav:"))
async def process_calendar_nav(callback: CallbackQuery):
    """
    Handles calendar month switching navigation.
    """
    await callback.answer()
    nav_str = callback.data.split(":")[2] # YYYY-MM
    year, month = map(int, nav_str.split("-"))
    
    new_keyboard = calendar_api.generate_calendar_keyboard(year, month)
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

@router.callback_query(F.data.startswith("cal:day:"))
async def process_calendar_day(callback: CallbackQuery, state: FSMContext):
    """
    Triggered when a client clicks on a specific date. Shows hourly slots.
    """
    await callback.answer()
    date_str = callback.data.split(":")[2] # YYYY-MM-DD
    print(f"DEBUG process_calendar_day: Date clicked: {date_str}, State: {await state.get_state()}")
    
    await state.update_data(selected_date=date_str)
    
    with get_db() as session:
        available_slots = calendar_api.get_available_slots(session, date_str)
        
    builder = InlineKeyboardBuilder()
    
    if len(available_slots) == 0:
        builder.row(InlineKeyboardButton(text="🔒 Нет свободных мест (Full)", callback_data="calendar_ignore"))
    else:
        slot_btns = []
        for slot in available_slots:
            slot_btns.append(InlineKeyboardButton(text=f"⏰ {slot}", callback_data=f"cal:slot:{slot}"))
        
        builder.add(*slot_btns)
        builder.adjust(3)
        
    builder.row(InlineKeyboardButton(text="◀️ Вернуться к календарю", callback_data="cal_return"))
    
    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
    greek_formatted_date = parsed_date.strftime("%d.%m.%Y")
    
    await callback.message.edit_text(
        f"📅 *Выбранная дата:* {greek_formatted_date}\n\n"
        f"⏰ Пожалуйста, выберите удобное время для записи:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "cal_return")
async def process_cal_return(callback: CallbackQuery):
    await callback.answer()
    calendar_markup = calendar_api.generate_calendar_keyboard()
    await callback.message.edit_text(
        "📅 Выберите подходящую дату на календаре ниже:",
        reply_markup=calendar_markup
    )

@router.callback_query(F.data.startswith("cal:slot:"))
async def process_calendar_slot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Triggered when client selects a time slot. Validates, creates DB entry, clears FSM, and notifies Admin.
    """
    await callback.answer()
    slot_str = callback.data.replace("cal:slot:", "") # HH:MM
    
    data = await state.get_data()
    selected_date = data.get("selected_date")
    print(f"DEBUG process_calendar_slot: Slot clicked: {slot_str}, State: {await state.get_state()}, Selected Date: {selected_date}, Data: {data}")
    
    if not selected_date:
        await callback.message.edit_text(
            "⚠️ Произошел сбой сессии. Пожалуйста, начните запись заново.",
            reply_markup=calendar_api.generate_calendar_keyboard()
        )
        await state.clear()
        return
        
    tg_id = callback.from_user.id
    username = callback.from_user.username
    fullname = callback.from_user.full_name
    
    with get_db() as session:
        still_free = calendar_api.get_available_slots(session, selected_date)
        if slot_str not in still_free:
            await callback.message.edit_text(
                "😔 Извините, это время только что забронировали. Выберите другое время:",
                reply_markup=calendar_api.generate_calendar_keyboard()
            )
            return
            
        new_appointment = Appointment(
            user_id=tg_id,
            date=selected_date,
            slot=slot_str,
            status="pending",
            hair_length=data.get("hair_length_type"),
            history_henna=data.get("history_henna"),
            history_box_dye=data.get("history_box_dye"),
            history_bleach=data.get("history_bleach"),
            desired_result=data.get("desired_result"),
            photo_path=data.get("photo_path"),
            trichology_report=data.get("trichology_report")
        )
        session.add(new_appointment)
        session.commit()
        appointment_id = new_appointment.id

    await state.clear()
    
    parsed_date = datetime.strptime(selected_date, "%Y-%m-%d")
    date_formatted = parsed_date.strftime("%d.%m.%Y")
    
    user_confirm_text = (
        f"🎉 *Заявка успешно отправлена!*\n\n"
        f"📅 *Дата:* {date_formatted}\n"
        f"⏰ *Время:* {slot_str}\n"
        f"👤 *Мастер:* Анфиса\n\n"
        f"⏳ Статус вашей заявки: *В ожидании подтверждения мастера (Pending)*.\n"
        f"Я отправлю вам уведомление, как только мастер одобрит или перенесет запись! ✨"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        user_confirm_text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    
    # --- ADMIN NOTIFICATION ---
    admin_text = (
        f"📅 *НОВАЯ ЗАЯВКА НА ЗАПИСЬ #{appointment_id}*\n\n"
        f"👤 *Клиент:* {fullname} (@{username or 'нет'})\n"
        f"🆔 *ID:* `{tg_id}`\n"
        f"📆 *Дата:* {date_formatted} ({slot_str})\n\n"
        f"📋 *Анкета клиента:*\n"
        f"• *Тип/Длина:* {data.get('hair_length_type', 'Не указано')}\n"
        f"• *Пожелания:* {data.get('desired_result', 'Без комментариев')}\n"
    )
    
    admin_kb = InlineKeyboardBuilder()
    admin_kb.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_appr:{appointment_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_rej:{appointment_id}")
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            if data.get("photo_path"):
                # First send the photo with a tiny caption (always safe from size limits)
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=data.get("photo_path"),
                    caption=f"📷 *Фото волос клиента к заявке #{appointment_id}*",
                    parse_mode="Markdown"
                )
                
                # Then send the full detailed text card with the admin buttons (up to 4096 chars)
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="Markdown",
                    reply_markup=admin_kb.as_markup()
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="Markdown",
                    reply_markup=admin_kb.as_markup()
                )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")


# --- Client Personal Cabinet Handlers ---

@router.callback_query(F.data == "client_cabinet")
async def show_client_cabinet(callback: CallbackQuery, state: FSMContext):
    """
    Renders client dashboard showing upcoming bookings and past visits history.
    Allows cancelling upcoming active appointments.
    """
    try:
        await callback.answer()
        await state.clear()  # Clear state just in case FSM is active
        
        import html
        tg_id = callback.from_user.id
        fullname = html.escape(callback.from_user.full_name)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        with get_db() as session:
            # Active upcoming appointments (approved or pending)
            upcoming = session.query(Appointment).filter(
                Appointment.user_id == tg_id,
                Appointment.date >= today_str,
                Appointment.status.in_(["approved", "pending"])
            ).order_by(Appointment.date, Appointment.slot).all()
            
            # Past or cancelled/completed appointments
            past = session.query(Appointment).filter(
                Appointment.user_id == tg_id,
                (Appointment.date < today_str) | (Appointment.status.in_(["completed", "cancelled"]))
            ).order_by(Appointment.date.desc(), Appointment.slot.desc()).limit(5).all()

            # Build active upcoming bookings section
            upcoming_lines = []
            builder = InlineKeyboardBuilder()
            
            if not upcoming:
                upcoming_text = "• <b>У вас нет активных предстоящих записей.</b>\n<i>Записаться на стрижку можно в главном меню с помощью удобного онлайн-календаря!</i>"
            else:
                upcoming_text = "<b>Ближайшие запланированные визиты:</b>\n"
                for app in upcoming:
                    parsed_dt = datetime.strptime(app.date, "%Y-%m-%d")
                    date_formatted = parsed_dt.strftime("%d.%m.%Y")
                    
                    status_desc = "🟢 Подтверждена" if app.status == "approved" else "🟡 В ожидании подтверждения мастера"
                    
                    safe_hair = html.escape(app.hair_length) if app.hair_length else 'Не указано'
                    safe_desired = html.escape(app.desired_result) if app.desired_result else 'Без комментариев'
                    
                    item_desc = (
                        f"📅 <b>{date_formatted} в {app.slot}</b>\n"
                        f"   • Статус: <i>{status_desc}</i>\n"
                        f"   • Пожелания: <i>{safe_hair} / {safe_desired}</i>\n"
                        f"   • Мастер: Анфиса"
                    )
                    upcoming_lines.append(item_desc)
                    
                    # Add an Inline button to cancel this specific appointment
                    cancel_btn_text = f"❌ Отменить {parsed_dt.strftime('%d.%m')} {app.slot}"
                    builder.row(InlineKeyboardButton(text=cancel_btn_text, callback_data=f"client_cancel_app:{app.id}"))
                    
                upcoming_text += "\n\n".join(upcoming_lines)

            # Build past visits history section
            if not past:
                past_text = "• <b>История посещений пуста.</b>"
            else:
                past_lines = []
                for app in past:
                    parsed_dt = datetime.strptime(app.date, "%Y-%m-%d")
                    date_formatted = parsed_dt.strftime("%d.%m.%Y")
                    
                    if app.status == "cancelled":
                        status_desc = "❌ Отменена"
                    elif app.status == "completed":
                        status_desc = "✅ Завершена"
                    else:
                        status_desc = "🔘 Прошедшая"
                        
                    past_lines.append(f"• <b>{date_formatted} в {app.slot}</b> — {status_desc}")
                past_text = "\n".join(past_lines)

            cabinet_html = (
                f"👤 <b>ЛИЧНЫЙ КАБИНЕТ КЛИЕНТА</b>\n\n"
                f"Здравствуйте, <b>{fullname}</b>! Рады видеть вас.\n\n"
                f"────────────────────\n"
                f"{upcoming_text}\n"
                f"────────────────────\n\n"
                f"📜 <b>ИСТОРИЯ ВАШИХ ВИЗИТОВ (до 5 последних):</b>\n"
                f"{past_text}\n\n"
                f"✨ <i>Если вам нужно отменить запись, нажмите на соответствующую кнопку ниже. "
                f"Запись будет сразу же удалена, освобождая время для других.</i>"
            )
            
            builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"))
            
            await callback.message.edit_text(
                cabinet_html,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
    except Exception as e:
        print(f"🔴 ERROR in show_client_cabinet: {e}")
        await callback.message.answer(
            "⚠️ <b>Произошла ошибка при открытии Личного кабинета.</b>\nПожалуйста, обратитесь к администратору студии.",
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("client_cancel_app:"))
async def process_client_cancel_prompt(callback: CallbackQuery):
    """
    Shows a double-confirmation prompt before cancelling an appointment.
    """
    try:
        await callback.answer()
        app_id = int(callback.data.split(":")[1])
        
        with get_db() as session:
            app = session.query(Appointment).filter(Appointment.id == app_id).first()
            if not app:
                await callback.message.edit_text(
                    "⚠️ <b>Ошибка: Запись не найдена.</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="👤 В личный кабинет", callback_data="client_cabinet")).as_markup()
                )
                return
                
            parsed_dt = datetime.strptime(app.date, "%Y-%m-%d")
            date_formatted = parsed_dt.strftime("%d.%m.%Y")
            slot_str = app.slot

        confirm_html = (
            f"❓ <b>ПОДТВЕРЖДЕНИЕ ОТМЕНЫ ЗАПИСИ</b>\n\n"
            f"Вы действительно хотите отменить вашу запись на <b>{date_formatted} в {slot_str}</b>?\n\n"
            f"⚠️ <i>Внимание: отмена действия необратима. Это время сразу же освободится в календаре, "
            f"и его сможет забронировать любой другой желающий!</i>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Да, отменить запись", callback_data=f"client_confirm_cancel:{app_id}"),
            InlineKeyboardButton(text="◀️ Нет, назад", callback_data="client_cabinet")
        )
        
        await callback.message.edit_text(
            confirm_html,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        print(f"🔴 ERROR in process_client_cancel_prompt: {e}")
        await callback.message.answer("⚠️ Ошибка при подготовке отмены записи. Пожалуйста, попробуйте позже.")

@router.callback_query(F.data.startswith("client_confirm_cancel:"))
async def process_client_confirm_cancel(callback: CallbackQuery, bot: Bot):
    """
    Performs the cancellation in DB, alerts client and all admins.
    """
    try:
        await callback.answer("Запись отменена.")
        app_id = int(callback.data.split(":")[1])
        
        tg_id = callback.from_user.id
        fullname = html.escape(callback.from_user.full_name)
        username = html.escape(callback.from_user.username) if callback.from_user.username else None
        
        with get_db() as session:
            app = session.query(Appointment).filter(Appointment.id == app_id).first()
            if not app:
                await callback.message.edit_text(
                    "⚠️ <b>Ошибка: Запись не найдена или уже была отменена.</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="👤 В кабинет", callback_data="client_cabinet")).as_markup()
                )
                return
                
            if app.status == "cancelled":
                await callback.message.edit_text(
                    "🟢 <b>Эта запись уже была отменена ранее.</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="👤 В кабинет", callback_data="client_cabinet")).as_markup()
                )
                return
                
            app.status = "cancelled"
            date_formatted = datetime.strptime(app.date, "%Y-%m-%d").strftime("%d.%m.%Y")
            slot_str = app.slot
            session.commit()
            
        # 1. Edit client's message with a confirmation
        success_html = (
            f"🗑️ <b>Запись успешно отменена</b>\n\n"
            f"Ваша запись на <b>{date_formatted} в {slot_str}</b> отменена.\n"
            f"Время освобождено. Ждем вас в следующий раз! ✨"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Вернуться к списку", callback_data="client_cabinet"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
        )
        
        await callback.message.edit_text(
            success_html,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        # 2. Notify all Admins in HTML to avoid Markdown underscore issues
        admin_alert_html = (
            f"🚨 <b>КЛИЕНТ ОТМЕНИЛ ЗАПИСЬ #{app_id}</b>\n\n"
            f"👤 <b>Клиент:</b> {fullname} (@{username or 'нет'})\n"
            f"🆔 <b>ID пользователя:</b> <code>{tg_id}</code>\n"
            f"📅 <b>Дата/время:</b> {date_formatted} в {slot_str}\n\n"
            f"❌ Временной слот автоматически освобожден и снова доступен для онлайн-записи других клиентов!"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_alert_html,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to alert admin {admin_id} about cancellation: {e}")
    except Exception as e:
        print(f"🔴 ERROR in process_client_confirm_cancel: {e}")
        await callback.message.answer("⚠️ Ошибка при выполнении отмены записи. Пожалуйста, обратитесь к мастеру.")
