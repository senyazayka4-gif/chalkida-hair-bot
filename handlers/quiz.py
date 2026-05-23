from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.connection import get_db
from database.models import User
import services.calendar_api as calendar_api
import services.trichology_advisor as trichology_advisor
import config


router = Router(name="quiz")

class HairQuiz(StatesGroup):
    length_and_type = State()
    history_henna = State()
    history_box_dye = State()
    history_bleach = State()
    desired_result = State()
    photo = State()

def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да (Yes)", callback_data="quiz_yes"),
        InlineKeyboardButton(text="❌ Нет (No)", callback_data="quiz_no")
    )
    return builder.as_markup()

def get_hair_specs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👩 Короткие / Тонкие (Short/Thin)", callback_data="hair:short_thin"))
    builder.row(InlineKeyboardButton(text="👩 Средние / Нормальные (Medium/Normal)", callback_data="hair:medium_normal"))
    builder.row(InlineKeyboardButton(text="👩 Длинные / Густые (Long/Thick)", callback_data="hair:long_thick"))
    builder.row(InlineKeyboardButton(text="👩 Кудрявые / Волнистые (Curly/Wavy)", callback_data="hair:curly_wavy"))
    return builder.as_markup()

@router.callback_query(F.data == "client_book")
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    """
    Triggers the FSM pre-appointment quiz.
    """
    await callback.answer()
    await state.clear()
    
    await state.set_state(HairQuiz.length_and_type)
    
    quiz_welcome = (
        "📋 *Анкета перед записью (Pre-Appointment Quiz)*\n\n"
        "Для того чтобы процедура стрижки или окрашивания прошла "
        "максимально безопасно и дала идеальный результат, пожалуйста, пройдите этот небольшой опрос для мастера.\n\n"
        "👇 *Шаг 1: Выберите длину и тип ваших волос:*"
    )
    
    await callback.message.edit_text(
        quiz_welcome,
        parse_mode="Markdown",
        reply_markup=get_hair_specs_keyboard()
    )

@router.callback_query(HairQuiz.length_and_type, F.data.startswith("hair:"))
async def process_hair_specs(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    hair_code = callback.data.split(":")[1]
    
    # Store length and type
    mapping = {
        "short_thin": "Короткие / Тонкие",
        "medium_normal": "Средние / Нормальные",
        "long_thick": "Длинные / Густые",
        "curly_wavy": "Кудрявые / Волнистые"
    }
    hair_specs = mapping.get(hair_code, "Не указано")
    await state.update_data(hair_length_type=hair_specs)
    
    await state.set_state(HairQuiz.history_henna)
    await callback.message.edit_text(
        "📋 *Анкета перед записью (Шаг 2 из 6)*\n\n"
        "Использовали ли вы *хну или басму* за последние 12 месяцев?\n"
        "_(Это критично, так как хна может дать непредсказуемый зеленый оттенок при осветлении)_",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )

@router.callback_query(HairQuiz.history_henna, F.data.in_(["quiz_yes", "quiz_no"]))
async def process_henna(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    answer = "Да" if callback.data == "quiz_yes" else "Нет"
    await state.update_data(history_henna=answer)
    
    await state.set_state(HairQuiz.history_box_dye)
    await callback.message.edit_text(
        "📋 *Анкета перед записью (Шаг 3 из 6)*\n\n"
        "Красили ли вы волосы *бытовыми красками из супермаркета* (коробками) за последние 12 месяцев?",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )

@router.callback_query(HairQuiz.history_box_dye, F.data.in_(["quiz_yes", "quiz_no"]))
async def process_box_dye(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    answer = "Да" if callback.data == "quiz_yes" else "Нет"
    await state.update_data(history_box_dye=answer)
    
    await state.set_state(HairQuiz.history_bleach)
    await callback.message.edit_text(
        "📋 *Анкета перед записью (Шаг 4 из 6)*\n\n"
        "Было ли у вас *полное осветление или сильное обесцвечивание порошком* за последние 12 месяцев?",
        parse_mode="Markdown",
        reply_markup=get_yes_no_keyboard()
    )

@router.callback_query(HairQuiz.history_bleach, F.data.in_(["quiz_yes", "quiz_no"]))
async def process_bleach(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    answer = "Да" if callback.data == "quiz_yes" else "Нет"
    await state.update_data(history_bleach=answer)
    
    await state.set_state(HairQuiz.desired_result)
    await callback.message.edit_text(
        "📋 *Анкета перед записью (Шаг 5 из 6)*\n\n"
        "Опишите желаемый результат (например: 'хочу холодный блонд', 'освежить каре', 'подровнять кончики'):\n\n"
        "✏️ *Напишите текст сообщением в чат:*",
        parse_mode="Markdown"
    )

@router.message(HairQuiz.desired_result)
async def process_desired_result(message: Message, state: FSMContext):
    await state.update_data(desired_result=message.text)
    
    await state.set_state(HairQuiz.photo)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭️ Пропустить фото (Skip)", callback_data="skip_photo"))
    
    await message.reply(
        "📋 *Анкета перед записью (Шаг 6 из 6)*\n\n"
        "Пожалуйста, пришлите **фото ваших волос** при хорошем освещении сзади (опционально).\n"
        "Это поможет мастеру лучше подготовиться к вашему визиту. ✨\n\n"
        "👇 Отправьте фото сообщением или нажмите кнопку пропуска:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@router.message(HairQuiz.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    # Save the largest photo file id
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_path=photo_file_id)
    await state.update_data(trichology_report=None)
    
    # Send a friendly confirmation
    await message.reply(
        "📸 *Фото волос успешно добавлено к вашей заявке!*\n"
        "Мастер обязательно изучит его перед вашей процедурой. ✨",
        parse_mode="Markdown"
    )
    
    # Show native calendar booking step
    await finish_quiz_and_show_calendar(message, state)

@router.callback_query(HairQuiz.photo, F.data == "skip_photo")
async def process_skip_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(photo_path=None)
    await finish_quiz_and_show_calendar(callback.message, state, is_callback=True)

async def finish_quiz_and_show_calendar(message: Message, state: FSMContext, is_callback: bool = False):
    """
    Finishes FSM, saves quiz data in states and triggers calendar view.
    """
    # Generate Calendar Keyboard for selection
    calendar_markup = calendar_api.generate_calendar_keyboard()
    
    instruction_text = (
        "📋 *Анкета успешно заполнена!*\n\n"
        "Спасибо, вся необходимая информация для мастера собрана.\n\n"
        "📅 *Шаг 7: Выберите дату вашего визита на календаре ниже:*"
    )
    
    if is_callback:
        await message.edit_text(instruction_text, parse_mode="Markdown", reply_markup=calendar_markup)
    else:
        await message.answer(instruction_text, parse_mode="Markdown", reply_markup=calendar_markup)
        
    # Set the FSM state to None so that the calendar handlers (which default to matching state=None)
    # can trigger successfully. The saved quiz data in FSM memory remains fully preserved!
    await state.set_state(None)
