# electro_parse

Парсер зображень графіків погодинних відключень електропостачання.

Скрипт читає зображення таблиці, визначає геометрію сітки, класифікує кольори клітинок і повертає структуру на кшталт:

```json
{
  "1.1": { "off": ["17:00", "18:00", "19:00", "20:00"], "maybe_off": [] },
  "1.2": { "off": ["17:00", "18:00", "19:00", "20:00"], "maybe_off": [] }
}
```

За замовчуванням парсер очікує матрицю `12 x 24`: 12 рядків підчерг і 24 погодинні колонки. Для такої конфігурації рядки маркуються як `1.1`, `1.2`, ..., `6.1`, `6.2`.

## Що вміє

- парсити зображення таблиці з налаштовуваною кількістю рядків і колонок;
- знаходити сітку як за заповненими клітинками, так і за лініями таблиці;
- повертати окремо години `off` і `maybe_off`;
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

Підтримувані в проєкті формати для вхідних файлів: `.jpg`, `.jpeg`, `.png`.

З debug-накладкою:

```bash
python electro_parse.py "images/photo_2026-03-19.jpeg" --debug
```

У цьому режимі debug-файл буде створено поруч з оригіналом, наприклад:

```text
images/photo_2026-03-19.debug.jpeg
```

Або з явним шляхом для debug-файлу:

```bash
python electro_parse.py "images/photo_2026-03-19.jpeg" --debug report/assets/photo_2026-03-19.debug.jpeg
```

Доступні параметри:

```bash
python electro_parse.py IMAGE --rows 12 --columns 24 --max-colors 10
```

Після успішного запуску скрипт друкує JSON у stdout. Якщо увімкнено `--debug`, додатково друкується шлях у форматі `debug_image=...`.

## Генерація звіту

```bash
python generate_report.py
```

Скрипт:

- бере всі файли `.jpg`, `.jpeg`, `.png` з директорії `images/`;
- ігнорує приховані файли та вже згенеровані `*.debug.*`;
- щоразу заново створює `report/assets/`;
- генерує `report/report.md` з відносними посиланнями на debug-зображення.

Можна змінити шляхи й параметри парсингу:

```bash
python generate_report.py --images images --report report --rows 12 --columns 24 --max-colors 10
```

## Тести

```bash
python -m unittest discover -s tests -v
```

Тести покривають:

- парсинг кількох реальних прикладів з `images/`;
- створення debug-накладки;
- генерацію Markdown-звіту з коректними відносними шляхами.

## Використання як бібліотеки

```python
from electro_parse import parse_schedule_image

data = parse_schedule_image("images/photo_2026-03-19.jpeg")
print(data["1.1"]["off"])
```

За потреби можна передати параметри явно:

```python
from electro_parse import parse_schedule_image

data = parse_schedule_image(
    "images/photo_2026-03-19.jpeg",
    row_count=12,
    column_count=24,
    max_colors=10,
    debug_output="report/assets/photo_2026-03-19.debug.jpeg",
)
```

## Приклад інтеграції в чатбот

```python
from electro_parse import parse_schedule_image


def handle_uploaded_schedule(image_path: str) -> dict:
    parsed = parse_schedule_image(image_path)
    return {
        "status": "ok",
        "schedule": parsed,
    }
```

Приклад відповіді по конкретній підчерзі:

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

- `electro_parse.py` — основний парсер і CLI;
- `generate_report.py` — генерація Markdown-звіту і debug-активів;
- `tests/` — unit-тести;
- `images/` — приклади вхідних зображень;
- `report/` — приклад згенерованого звіту.
