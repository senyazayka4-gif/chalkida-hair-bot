from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from database.connection import get_db
from database.models import User
import config

router = Router(name="common")

def get_client_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться онлайн", callback_data="client_book"))
    builder.row(InlineKeyboardButton(text="👤 Личный кабинет", callback_data="client_cabinet"))
    builder.row(InlineKeyboardButton(text="🖼️ Наше Портфолио и Цены", callback_data="client_portfolio"))
    builder.row(InlineKeyboardButton(text="📍 Адрес и Контакты", callback_data="client_contacts"))
    return builder.as_markup()

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Предстоящие записи", callback_data="admin_view_bookings"))
    builder.row(InlineKeyboardButton(text="🔒 Управление слотами", callback_data="admin_block_time"))
    builder.row(InlineKeyboardButton(text="📢 Настройки OSINT-парсера", callback_data="admin_osint"))
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handles /start command.
    """
    tg_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    with get_db() as session:
        user = User.get_or_create(
            session=session,
            tg_id=tg_id,
            username=username,
            fullname=fullname
        )
        
        # Check if user is config admin, update flag in DB if not set
        if tg_id in config.ADMIN_IDS and not user.is_admin:
            user.is_admin = True
            session.commit()
            
        is_admin = user.is_admin

    if is_admin:
        await message.reply(
            f"👑 *Добро пожаловать в Админ-панель, {fullname}!*\n\n"
            f"Здесь вы можете управлять записями вашей жены, блокировать часы "
            f"и просматривать лиды, найденные фоновым парсером в чатах Греции.",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )
    else:
        welcome_text = (
            f"👋 *Привет, {fullname}!* Вас приветствует профессиональный парикмахер в Халкиде! 💇‍♀️✨\n\n"
            f"🏠 Делаю практичные и качественные *стрижки, не требующие сложной укладки*, у себя на дому (г. Халкида) "
            f"либо с выездом к вам домой (недалеко от Халкиды).\n\n"
            f"👇 Выберите нужное действие в меню ниже:"
        )

        await message.reply(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_client_menu_keyboard()
        )

@router.callback_query(F.data == "back_to_menu")
async def process_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """
    Returns user to the main menu and clears FSM states.
    """
    await callback.answer()
    await state.clear()
    tg_id = callback.from_user.id
    fullname = callback.from_user.full_name
    
    with get_db() as session:
        user = session.query(User).filter(User.tg_id == tg_id).first()
        is_admin = user.is_admin if user else (tg_id in config.ADMIN_IDS)

    if is_admin:
        await callback.message.edit_text(
            f"👑 *Админ-панель, {fullname}:*",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"👋 *Главное меню, {fullname}:*\n\nВыберите нужное действие:",
            parse_mode="Markdown",
            reply_markup=get_client_menu_keyboard()
        )

@router.callback_query(F.data == "client_contacts")
async def show_contacts(callback: CallbackQuery):
    """
    Shows contact details and mobile/home options in Chalkida.
    """
    await callback.answer()
    contacts_text = (
        "📍 *Локация и Контакты:*\n\n"
        "🏠 *Где проходят стрижки:* У нас на дому в Халкиде (недалеко от центра) или *с выездом к вам* домой (Халкида и ближайший пригород)\n"
        "📞 *Связь с мастером:* напрямую через Telegram после подтверждения записи\n"
        "📅 *Часы работы:* по предварительной договоренности и онлайн-записи\n\n"
        "💇‍♀️ *Буду рада преобразить ваши волосы!*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"))
    
    await callback.message.edit_text(
        contacts_text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup(),
        disable_web_page_preview=False
    )
