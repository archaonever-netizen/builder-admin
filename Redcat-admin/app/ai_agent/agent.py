import os
import re
import io
import json
import requests
import PyPDF2
import docx
from openai import OpenAI
from flask import current_app
from urllib.parse import urlparse, unquote

SYSTEM_PROMPT = """
Ты специалист по составлению регламентов. Работаешь в компании RedCat.
Тебе нужно составлять регламенты фиксации и бронирования клиентов на основе предоставленного документа (агентского договора или приложений к нему).
... (полный текст промпта остаётся без изменений, как в последней версии)
"""

def extract_text_from_url(url):
    """Извлекает текст из файла, доступного по URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Извлекаем имя файла из URL, очищая query-параметры
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = path.split('/')[-1]
        # Удаляем возможный "?" и всё после него
        filename = filename.split('?')[0]
        ext = os.path.splitext(filename)[1].lower()
        file_content = io.BytesIO(response.content)

        if ext == '.pdf':
            reader = PyPDF2.PdfReader(file_content)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
            if not text.strip():
                raise ValueError("PDF не содержит текстового слоя (возможно, скан).")
            return text
        elif ext in ('.docx', '.doc'):
            doc = docx.Document(file_content)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    full_text.append(' | '.join(row_data))
            for section in doc.sections:
                header = section.header
                if header:
                    for para in header.paragraphs:
                        if para.text.strip():
                            full_text.append(para.text.strip())
                footer = section.footer
                if footer:
                    for para in footer.paragraphs:
                        if para.text.strip():
                            full_text.append(para.text.strip())
            return '\n'.join(full_text)
        elif ext == '.txt':
            return response.text
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")
    except Exception as e:
        raise ValueError(f"Не удалось извлечь текст из документа: {e}")

def process_agency_agreement(url):
    """Обрабатывает агентский договор, доступный по публичному URL."""
    try:
        text = extract_text_from_url(url)
        if not text.strip():
            raise ValueError("Извлечённый текст пуст.")
    except Exception as e:
        current_app.logger.error(f"[AI AGENT] Ошибка извлечения текста: {e}")
        raise

    current_app.logger.info(f"[AI AGENT] Extracted text (first 800 chars): {text[:800]}")

    client = OpenAI(
        api_key=current_app.config['OPENROUTER_API_KEY'],
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://builder-admin-q7mb.onrender.com",
            "X-Title": "RedCat CRM"
        }
    )

    try:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Документ:\n{text[:15000]}"}
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    if response.choices and len(response.choices) > 0:
        answer = response.choices[0].message.content
    else:
        current_app.logger.error(f"[AI AGENT] OpenRouter returned empty choices: {response}")
        raise ValueError("OpenRouter returned empty response")
except Exception as e:
    current_app.logger.error(f"[AI AGENT] Ошибка вызова OpenRouter: {e}")
    raise

    try:
        json_match = re.search(r'\{.*\}', answer, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        else:
            current_app.logger.warning("[AI AGENT] JSON не найден в ответе, возвращаю raw_response.")
            return {"raw_response": answer}
    except Exception as e:
        current_app.logger.error(f"[AI AGENT] Ошибка парсинга JSON: {e}")
        return {"raw_response": answer}
