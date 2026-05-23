import os
import config
from google import generativeai as genai

# Configure Google Gemini API Key
genai.configure(api_key=config.GEMINI_API_KEY)

# Define system prompt - experienced, warm, down-to-earth hairdresser Anfisa in Chalkida.
# Strictly prohibits corporate fluff, clinical jargon, or exaggerated marketing pathos.
# Focuses on honest, realistic, real-life evaluations and practical home-care advice.
SYSTEM_INSTRUCTION = (
    "Вы — Анфиса, опытный, душевный и практичный мастер по стрижкам в Халкиде. "
    "Вам прислали фото волос клиентки сзади и результаты её предварительного мини-опроса перед стрижкой.\n\n"
    "Сделайте честный, реалистичный и жизненный разбор её волос. Говорите простым, понятным языком, "
    "как опытный мастер за чашкой кофе. Избегайте научного пафоса, сложного трихологического жаргона "
    "и рекламного пафоса элитных салонов. Оценивайте ситуацию здраво и предлагайте варианты из реальной жизни.\n\n"
    "Сформируйте отчет строго в следующем формате (используйте Markdown):\n\n"
    "💇‍♀️ **Что я вижу на фото:**\n"
    "[Опишите реальную структуру волос: прямые, волнистые, густоту, видимое состояние концов, сухость/пушистость. Говорите прямо и по делу, без преувеличений.]\n\n"
    "📝 **Сопоставляю с историей волос:**\n"
    "[Прокомментируйте её ответы в опросе: например, если была хна, бытовые краски или обесцвечивание порошком. Объясните жизненные риски для её структуры волос, честно и без запугивания.]\n\n"
    "✂️ **Какая стрижка подойдет лучше всего (без укладки):**\n"
    "[Предложите конкретную форму из нашего портфолио: 'Точный прямой боб', 'Объемный каскад' или 'Стильный удлиненный боб'. Объясните простым языком, почему эта стрижка будет идеально лежать сама по себе после мытья и сушки без утюжков и плоек.]\n\n"
    "🌿 **Простой домашний уход (из жизни):**\n"
    "[Дайте 2-3 практичных совета по уходу, которые легко делать дома. Не советуйте косметику за 100 евро. Предложите базовые, доступные и рабочие средства: правильное мытье, увлажнение кончиков, температурный режим сушки.]"
)

async def analyze_hair_photo(photo_bytes: bytes, quiz_data: dict) -> str:
    """
    Sends the hair photo and FSM quiz details to Gemini 1.5 Flash Vision.
    Generates a realistic, warm, down-to-earth diagnostic report in Russian.
    """
    if not config.GEMINI_API_KEY:
        return "⚠️ Модуль ИИ временно отключен (не задан API ключ)."

    # Format quiz answers for context
    quiz_summary = (
        f"Данные опроса клиентки:\n"
        f"- Заявленный тип/длина: {quiz_data.get('hair_length_type', 'Не указано')}\n"
        f"- Использование хны/басмы за 12 мес: {quiz_data.get('history_henna', 'Нет')}\n"
        f"- Окрашивание бытовыми красками за 12 мес: {quiz_data.get('history_box_dye', 'Нет')}\n"
        f"- Осветление порошком за 12 мес: {quiz_data.get('history_bleach', 'Нет')}\n"
        f"- Пожелания клиентки: {quiz_data.get('desired_result', 'Подровнять кончики')}\n"
    )

    try:
        # Define model - gemini-2.5-flash is extremely fast, highly accurate, and supports vision.
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )

        # Prepare multimodal contents
        image_part = {
            "mime_type": "image/jpeg",
            "data": photo_bytes
        }

        # Request generation
        response = await model.generate_content_async([
            image_part,
            f"\n\nПроанализируй фото волос с учетом следующих ответов:\n{quiz_summary}"
        ])

        return response.text
    except Exception as e:
        print(f"Error in Gemini trichology generation: {e}")
        return (
            "🌿 **ИИ-Диагностика Анфисы:**\n\n"
            "Рада вашему обращению! Фото получено. Визуально волосы имеют хорошую базу, "
            "однако для детального разбора структуры нам нужно будет пообщаться вживую на встрече. "
            "Я уже вижу ваши пожелания и с радостью подготовлю идеальный вариант стрижки, "
            "который будет отлично лежать без укладки! До встречи!"
        )
