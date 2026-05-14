import os
from openai import OpenAI
import json
import PyPDF2
import docx
from flask import current_app
import requests
import io

SYSTEM_PROMPT = """
Ты специалист по составлению регламентов. Работаешь в компании RedCat.
Тебе нужно составлять регламенты, по которым с нами работают застройщики.
Тебя интересуют регламенты фиксации и бронирования клиента (каким образом нам сделать так, чтобы клиент, которого мы находим, был зафиксирован за нами).
Тебе поступил документ. Нужно выявить регламент фиксации и бронирования и заполнить его в соответствии с формой.
ФОРМА (строго JSON):
{
  "internal_regulation": {
    "company": "",
    "fixation_address": "",
    "fixation_period": "",
    "commerce_fixation": "",
    "foreign_numbers_fixation": "",
    "cross_fixation": "",
    "fixation_start": "",
    "uniqueness_extension": "",
    "viewing_appointment": "",
    "escort_required": "",
    "inspection_report_required": "",
    "developer_emails": "",
    "response_time": "",
    "notes": ""
  },
  "booking_regulation": {
    "how_to_update_tariffs": "",
    "how_to_update_remains": ""
  }
}
Заполни ТОЛЬКО те поля, которые явно упомянуты в документе. Не придумывай ничего лишнего.
"""

def extract_text_from_url(url):
    """Извлекает текст из файла, доступного по URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Определяем тип файла по расширению в URL
        filename = url.split('/')[-1]
        ext = os.path.splitext(filename)[1].lower()
        
        # Сохраняем контент в BytesIO для обработки
        file_content = io.BytesIO(response.content)
        
        if ext == '.pdf':
            reader = PyPDF2.PdfReader(file_content)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
            return text
        elif ext in ('.docx', '.doc'):
            doc = docx.Document(file_content)
            return '\n'.join([para.text for para in doc.paragraphs])
        else:
            return response.text
    except Exception as e:
        raise ValueError(f"Не удалось извлечь текст из документа: {e}")

def process_agency_agreement(url):
    """Обрабатывает агентский договор, доступный по публичному URL."""
    text = extract_text_from_url(url)
    if not text.strip():
        raise ValueError("Не удалось извлечь текст из документа")

    client = OpenAI(
        api_key=current_app.config['OPENROUTER_API_KEY'],
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://builder-admin-q7mb.onrender.com",  # Ваш актуальный URL
            "X-Title": "RedCat CRM"
        }
    )

    response = client.chat.completions.create(
        model="google/gemini-2.5-flash-lite-preview-05-06:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Документ:\n{text[:15000]}"}
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    answer = response.choices[0].message.content
    try:
        start = answer.index('{')
        end = answer.rindex('}') + 1
        json_str = answer[start:end]
        data = json.loads(json_str)
        return data
    except:
        return {"raw_response": answer}
