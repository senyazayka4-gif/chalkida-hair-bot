from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import services.calendar_api as calendar_api
import config

router = Router(name="quiz")

def get_style_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard listing the premium hairstyles from config.PORTFOLIO_ITEMS
    plus a custom booking option.
    """
    builder = InlineKeyboardBuilder()
    
    # Loop over current configured portfolio items
    for item in config.PORTFOLIO_ITEMS:
        builder.row(InlineKeyboardButton(text=item["title"], callback_data=f"client_book_style:{item['id']}"))
        
    builder.row(InlineKeyboardButton(text="💇‍♀️ Другая стрижка / Свой вариант", callback_data="client_book_style:other"))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_menu"))
    return builder.as_markup()

@router.callback_query(F.data == "client_book")
async def start_booking_flow(callback: CallbackQuery, state: FSMContext):
    """
    Triggered when clicking "Записаться онлайн" from main menu.
    Asks the client to select their desired hairstyle.
    """
    await callback.answer()
    await state.clear()
    
    welcome_text = (
        "💇‍♀️ *ВЫБОР СТРИЖКИ ДЛЯ ЗАПИСИ*\n\n"
        "Пожалуйста, выберите прическу, которую вы хотите сделать:\n\n"
        "ℹ️ _Посмотреть примеры работ и подробное описание можно в разделе «🖼️ Наше Портфолио и Цены» в главном меню._"
    )
    
    try:
        await callback.message.edit_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_style_selection_keyboard()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_style_selection_keyboard()
        )

@router.callback_query(F.data.startswith("client_book_style:"))
async def process_style_booking(callback: CallbackQuery, state: FSMContext):
    """
    Triggered when a specific hairstyle is chosen from the menu or portfolio.
    Presets FSM state data and instantly loads the calendar.
    """
    await callback.answer()
    style_id = callback.data.replace("client_book_style:", "")
    
    style_name = "Свой вариант"
    # Find matching style title from config
    for item in config.PORTFOLIO_ITEMS:
        if item["id"] == style_id:
            style_name = item["title"]
            break
            
    if style_id == "other":
        style_name = "Свой вариант / Другая стрижка"
        
    # Preset FSM context variables to maintain absolute backward compatibility with the database schema
    await state.update_data(
        hair_length_type=style_name,
        history_henna="Нет",
        history_box_dye="Нет",
        history_bleach="Нет",
        desired_result=f"Выбрана стрижка: {style_name}",
        photo_path=None,
        trichology_report=None
    )
    
    # Generate Calendar Keyboard for selection
    calendar_markup = calendar_api.generate_calendar_keyboard()
    
    instruction_text = (
        f"📋 *Выбранная услуга:* {style_name}\n\n"
        f"📅 *Пожалуйста, выберите подходящую дату на календаре ниже:*"
    )
    
    # Release FSM state block so that direct calendar handlers match successfully,
    # while keeping the updated state data stored safely in memory.
    await state.set_state(None)
    
    try:
        await callback.message.edit_text(
            instruction_text,
            parse_mode="Markdown",
            reply_markup=calendar_markup
        )
    except Exception:
        # If it fails (e.g. attempting to edit a photo message into text), delete and send fresh
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            instruction_text,
            parse_mode="Markdown",
            reply_markup=calendar_markup
        )
