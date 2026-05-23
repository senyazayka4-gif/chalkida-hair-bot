import calendar
from datetime import datetime, date, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.models import Appointment

GREEK_MONTHS = {
    1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος", 4: "Απρίλιος",
    5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
    9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
}

GREEK_WEEKDAYS = ["Δε", "Τρ", "Τε", "Πε", "Πα", "Σα", "Κυ"]

DEFAULT_SLOTS = ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]

def get_available_slots(session, date_str: str) -> list[str]:
    """
    Queries database for already booked appointments on a given date (YYYY-MM-DD).
    Returns a list of remaining available slots.
    """
    # Fetch all appointments for the date that are active (pending or approved)
    booked_appointments = session.query(Appointment).filter(
        Appointment.date == date_str,
        Appointment.status.in_(["pending", "approved"])
    ).all()
    
    booked_slots = [app.slot for app in booked_appointments]
    
    # Return slots that are NOT booked
    return [slot for slot in DEFAULT_SLOTS if slot not in booked_slots]


def generate_calendar_keyboard(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """
    Generates a dynamic inline calendar keyboard for a specific month/year.
    Days in the past are unclickable.
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    builder = InlineKeyboardBuilder()
    
    # --- Row 1: Month and Year Header ---
    month_name = GREEK_MONTHS.get(month, "Month")
    header_btn = InlineKeyboardButton(
        text=f"✨ {month_name} {year} ✨",
        callback_data="calendar_ignore"
    )
    builder.row(header_btn)
    
    # --- Row 2: Weekday Headers ---
    weekday_btns = [InlineKeyboardButton(text=w, callback_data="calendar_ignore") for w in GREEK_WEEKDAYS]
    builder.row(*weekday_btns)
    
    # --- Days Matrix ---
    month_calendar = calendar.monthcalendar(year, month)
    today = date.today()
    
    for week in month_calendar:
        week_btns = []
        for day in week:
            if day == 0:
                # Empty cell for padding
                week_btns.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))
            else:
                day_date = date(year, month, day)
                if day_date < today:
                    # Past days are muted and unclickable
                    week_btns.append(InlineKeyboardButton(text="❌", callback_data="calendar_ignore"))
                else:
                    # Clickable active day
                    date_str = day_date.strftime("%Y-%m-%d")
                    week_btns.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:day:{date_str}"))
        builder.row(*week_btns)
        
    # --- Navigation Controls ---
    # Calc prev month
    prev_date = datetime(year, month, 1) - timedelta(days=1)
    # Calc next month
    next_date = datetime(year, month, 28) + timedelta(days=7) # Go to next month
    next_date = datetime(next_date.year, next_date.month, 1)
    
    nav_btns = []
    
    # Don't show prev button if the displayed month is the current month
    if year == now.year and month == now.month:
        nav_btns.append(InlineKeyboardButton(text="🔒", callback_data="calendar_ignore"))
    else:
        prev_str = prev_date.strftime("%Y-%m")
        nav_btns.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cal:nav:{prev_str}"))
        
    # Add Menu Button
    nav_btns.append(InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu"))
    
    next_str = next_date.strftime("%Y-%m")
    nav_btns.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"cal:nav:{next_str}"))
    
    builder.row(*nav_btns)
    
    return builder.as_markup()
