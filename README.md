# Kittygram backend

Курсовой бэкенд: котики как в базовом Kittygram (`/cats/`) + квесты по неделям под `/api/`.

Стек: Django 5.1, DRF, SQLite, токены, Swagger/ReDoc (drf-spectacular), docker-compose.

## Как запустить локально

### Windows (PowerShell)

```powershell
cd путь\к\kittygram2
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo_quest
python manage.py runserver
```

Если `Activate.ps1` ругается на политику выполнения: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (один раз). В **cmd** вместо активации: `.venv\Scripts\activate.bat`; копия env: `copy .env.example .env`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
cp .env.example .env       # macOS / Linux
python manage.py migrate
python manage.py seed_demo_quest
python manage.py runserver
```

Swagger: http://127.0.0.1:8000/api/schema/swagger-ui/  
ReDoc: http://127.0.0.1:8000/api/schema/redoc/

## Docker

```bash
docker compose up --build
```

Порт 8000. Внутри контейнера staff можно так:  
`docker compose exec web python manage.py promote_staff <логин>`

## Тестовые данные

`python manage.py seed_demo_quest` — неделя `demo-week` на текущую календарную неделю + 2 шага (если их ещё нет).

## Логин в API

Токен: заголовок `Authorization: Token <...>`

- `POST /api/auth/register/` — `username`, `password`, опционально `staff_key`
- `POST /api/auth/token/` — существующий пользователь

### Staff без админки

В `.env` положи `REGISTER_STAFF_KEY=...` (см. `.env.example`).

При регистрации добавь в JSON то же значение в `staff_key` — в ответе `is_staff: true`.  
Либо уже с токеном: `POST /api/auth/promote-self/` с `{"staff_key":"..."}`.

Если ключ в `.env` пустой — через API staff не выдаётся.

В терминале можно: `python manage.py promote_staff <username>`.

## Старый API котиков

- `GET /cats/` — список  
- `POST /cats/` — `name`, `color`, `birth_year` (год не обязателен)

В Swagger это отдельная группа `cats`.

## Основные URL под `/api/`

| Метод | Путь | Кто |
|-------|------|-----|
| GET | `/api/quest-weeks/` | все; не-staff видят только опубликованные |
| POST | `/api/quest-weeks/` | staff |
| GET/PATCH/PUT/DELETE | `/api/quest-weeks/{id}/` | GET как выше; правки staff |
| GET | `/api/quest-weeks/current/` | все |
| POST | `/api/quest-weeks/{id}/enroll/` | с токеном |
| GET | `/api/quest-weeks/{id}/leaderboard/` | все |
| CRUD | `/api/quest-steps/` | чтение всем (с ограничениями); запись staff |
| GET/PATCH | `/api/participations/` | свой список; PATCH только `status: dropped` |
| POST | `/api/participations/{id}/complete_step/` | владелец, тело `{"step_id": N}` |
| GET | `/api/step-progress/` | свой прогресс |

Админка `/admin/` не обязательна для сценария с ключом выше.

## Postman

Файл `postman/Kittygram.postman_collection.json` — импорт в Postman, переменные `token`, `participation_id` и т.д.

## Тесты

```bash
python manage.py test quests.tests
```

## Переменные

Смотри `.env.example` (SECRET_KEY, DEBUG, ALLOWED_HOSTS, PAGE_SIZE, SQLITE_NAME, REGISTER_STAFF_KEY).

## Про версию Django

В шаблоне проекта был Django 3.2; здесь Django 5.1 (удобнее на свежем Python) — для курсовой разницы почти нет.
