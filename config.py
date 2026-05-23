import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(dotenv_path=ENV_PATH)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API_SERVER = os.getenv("TELEGRAM_API_SERVER", "")

# Admin IDs (list of telegram IDs of managers who approve appointments and receive OSINT leads)
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]

# Gemini AI Key for fast lead answers
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Telethon API details (needed for local background chat parsing)
TELETHON_API_ID = os.getenv("TELETHON_API_ID", "")
if TELETHON_API_ID.isdigit():
    TELETHON_API_ID = int(TELETHON_API_ID)
else:
    TELETHON_API_ID = None

TELETHON_API_HASH = os.getenv("TELETHON_API_HASH", "")

# Database Config
DB_URL = os.getenv("DB_URL", f"sqlite:///{BASE_DIR}/database/chalkida_hair.db")

# OSINT Keywords for Client Hunting (using robust substring matching)
KEYWORDS_GR = [
    "κομμωτήριο", "κούρεμα", "χαλκίδα", "εύβοια", "κομμώτρια", 
    "χτένισμα", "σαλόνι ομορφιάς", "μαλλιά", "κομμωτής", "κoμμωτήριο"
]

KEYWORDS_EN = [
    "hairdresser", "haircut", "chalkida", "evia", "hair", 
    "salon", "stylist", "coiffeur"
]

KEYWORDS_RU = [
    "парикмахер", "стриж", "салон красоты", 
    "прическ", "укладк", "подстричь", "волос"
]

KEYWORDS_UA = [
    "перукар", "стриж", "салон краси", 
    "зачіск", "укладк", "підстриг", "волос"
]

# Monitored Telegram channels/groups by default (Chalkida / Evia local groups)
# Monitored Telegram channels/groups by default (premium expat channels)
DEFAULT_MONITORED_CHANNELS = [
    "NASHI_v_GRETSII",
    "Residence_permit_gr",
    "greece4ukraine",
    "greece_russia",
    "greeceforukraine",
    "helpukrainegr",
    "russians_in_greece",
    "ua24gr",
    "ukrainianshelp"
]

# Hairdresser Portfolio (Services & Styles)
PORTFOLIO_ITEMS = [
    {
        "id": "style_bob",
        "title": "💇‍♀️ Классическое Каре (Bob Haircut)",
        "description": "Точное, безупречное классическое каре, которое идеально держит форму без укладки. Отличный выбор для прямых или слегка волнистых волос.",
        "duration": "1 час",
        "price": "15-20€",
        "photo": "https://raw.githubusercontent.com/senyazayka4-gif/chalkida-hair-bot/main/assets/bob_haircut.png"
    },
    {
        "id": "style_pixie",
        "title": "💇‍♀️ Текстурный Пикси (Modern Pixie)",
        "description": "Стильная, смелая и ультрапрактичная короткая стрижка, которая подчеркивает черты лица и не требует абсолютно никакого ухода.",
        "duration": "1 час",
        "price": "15-20€",
        "photo": "https://raw.githubusercontent.com/senyazayka4-gif/chalkida-hair-bot/main/assets/pixie_haircut.png"
    },
    {
        "id": "style_long_bob",
        "title": "💇‍♀️ Удлиненное Каре (Long Bob / Lob)",
        "description": "Элегантное удлиненное каре, плавно спускающееся к плечам. Идеально сбалансированная стрижка, которая прекрасно вытягивает силуэт и выглядит роскошно даже без укладки.",
        "duration": "1 час",
        "price": "15-20€",
        "photo": "https://raw.githubusercontent.com/senyazayka4-gif/chalkida-hair-bot/main/assets/long_bob_haircut.png"
    },
    {
        "id": "style_straight",
        "title": "💇‍♀️ Ровный срез (Blunt Straight Cut)",
        "description": "Идеально прямой, плотный и геометрически точный срез для длинных волос, создающий эффект густоты и глянцевого блеска.",
        "duration": "1 час",
        "price": "15-20€",
        "photo": "https://raw.githubusercontent.com/senyazayka4-gif/chalkida-hair-bot/main/assets/straight_haircut.png"
    }
]

# Telegram Mini App Configuration
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://anfisa-hair-artistry.surge.sh/booking.html")


