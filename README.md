# electro_parse

Парсер JPG/PNG з графіками погодинних відключень електропостачання.

Скрипт шукає основну матрицю розкладу, визначає геометрію сітки, читає кольори клітинок і повертає структуру:

```json
{
  "1.1": { "off": ["19:00", "20:00"], "maybe_off": [] },
  "1.2": { "off": [], "maybe_off": [] }
}
```

## Що вміє

- парсити таблицю `24 x M` з погодинними колонками;
- працювати з трохи різними стилями таблиці;
- будувати debug-зображення з накладеною знайденою сіткою;
- генерувати Markdown-звіт по всіх зображеннях з `images/`.

## Встановлення

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Запуск парсера

Базовий запуск:

```bash
python electro_parse.py "images/photo_2026-03-19.jpeg"
```

З debug-накладкою:

```bash
python electro_parse.py "images/photo_2026-03-19.jpeg" --debug
```

Або з явним шляхом для debug-файлу:

```bash
python electro_parse.py "images/photo_2026-03-19.jpeg" --debug report/assets/photo_2026-03-19.debug.jpeg
```

## Генерація звіту

```bash
python generate_report.py
```

Результат:

- `report/report.md`
- `report/assets/*.debug.jpeg`

У `report.md` зображення вставляються відносними шляхами `assets/...`, тому це коректно працює на GitHub.

## Тести

```bash
python -m unittest discover -s tests -v
```

## Використання як бібліотеки

Парсер можна імпортувати в інший Python-проєкт:

```python
from electro_parse import parse_schedule_image

data = parse_schedule_image("images/photo_2026-03-19.jpeg")
print(data["1.1"]["off"])
```

## Приклад інтеграції в чатбот

Сценарій:

1. користувач надсилає боту зображення графіка;
2. бот зберігає файл тимчасово на диск;
3. код викликає `parse_schedule_image(...)`;
4. бот повертає структуровані дані або текстову відповідь.

Мінімальний приклад:

```python
from electro_parse import parse_schedule_image


def handle_uploaded_schedule(image_path: str) -> dict:
    parsed = parse_schedule_image(image_path)
    return {
        "status": "ok",
        "schedule": parsed,
    }


result = handle_uploaded_schedule("/tmp/uploaded-schedule.jpeg")
print(result)
```

Приклад, якщо чатботу треба відповісти по конкретній підчерзі:

```python
from electro_parse import parse_schedule_image


def build_queue_answer(image_path: str, queue: str) -> str:
    parsed = parse_schedule_image(image_path)
    queue_data = parsed[queue]

    off = ", ".join(queue_data["off"]) or "немає"
    maybe_off = ", ".join(queue_data["maybe_off"]) or "немає"

    return (
        f"Підчерга {queue}. "
        f"Відключення: {off}. "
        f"Можливі відключення: {maybe_off}."
    )
```

## Структура проєкту

- `electro_parse.py` — основний парсер;
- `generate_report.py` — генерація Markdown-звіту і debug-активів;
- `tests/` — тести;
- `images/` — приклади вхідних зображень;
- `report/` — згенерований звіт.
