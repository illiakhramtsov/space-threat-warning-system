# Система попередження про космічні загрози (Варіант 9 — EDA)

Повний навчальний проєкт для лабораторних робіт №1–№6 з дисципліни проєктування високонавантажених систем.

## Структура репозиторію
- `src/app/` — вихідний код бекенду на FastAPI (моделі, схеми, маршрути, EDA-брокер, RBAC/IDOR).
- `tests/` — юніт- та інтеграційні тести `pytest` (401, 200/401, 403 Vertical, 403 Horizontal IDOR, 500 masking).
- `config/` — файли змінних оточення (`.env.sandbox`, `.env.production.example`, `.env.docker`).
- `docs/` — архітектурна документація та графічні діаграми (`architecture_diagram.png`, `nginx_lb_architecture.png`).
- `load_tests/` — сценарії навантажувального тестування Locust та генератор графіків (`plot_results.py`).
- `nginx/` — конфігурації балансувальника Nginx (`Round Robin`, `least_conn`, `weighted`, `ip_hash`).
- `scripts/` — скрипт наповнення БД (`seed_data.py`) та скрипт перевірки балансування (`test_load_balancer.py`).
- `.github/workflows/ci.yml` — CI-пайплайн GitHub Actions.

---

## 1. Локальне встановлення (ЛР №1–№2)
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

### Налаштування pre-commit хуків (ЛР №1, додаткове завдання)
```bash
git init
pre-commit install
pre-commit run --all-files
```

### Запуск тестів (ЛР №2)
```bash
pytest
```

---

## 2. Запуск у середовищах Sandbox та Production (ЛР №3)

### Режим Sandbox (DEBUG=True, ізольована БД `space_threats_sandbox.db`, Swagger `/docs` увімкнено)
**Linux / macOS:**
```bash
APP_ENV=sandbox uvicorn --app-dir src app.main:app --reload --port 8000
```
**Windows PowerShell:**
```powershell
$env:APP_ENV="sandbox"
uvicorn --app-dir src app.main:app --reload --port 8000
```
Наповнення тестовими даними (адмін `admin` / `AdminSpace2026!`, оператор `operator1` / `Operator2026!`):
```bash
python scripts/seed_data.py
```

### Режим Production (DEBUG=False, PostgreSQL, `/docs` вимкнено, стектрейси приховані)
1. Скопіюйте `config/.env.production.example` у `config/.env.production` та задайте власні `SECRET_KEY` і `DATABASE_URL`.
2. Запустіть сервер без режиму `--reload`:
```bash
APP_ENV=production uvicorn --app-dir src app.main:app --host 0.0.0.0 --port 8000 --workers 2
```
3. Перевірка приховування стектрейсів: відкрийте `GET http://localhost:8000/api/v1/system/simulate-error` — сервер поверне безпечний JSON `{"detail": "Internal Server Error"}` без трейсбеку.

---

## 3. Навантажувальне тестування з Locust (ЛР №4)
Запустіть веб-інтерфейс Locust (http://localhost:8089):
```bash
locust -f load_tests/locustfile.py --host http://localhost:8000
```
Або автоматизований headless-прогон із генерацією HTML-звіту, CSV та PNG-графіків:
```bash
# Linux/macOS:
bash load_tests/run_load_test.sh http://localhost:8000 100 10 1m
# Windows PowerShell:
.\load_tests\run_load_test.ps1 -HostUrl http://localhost:8000 -Users 100 -SpawnRate 10 -Duration 1m
```

---

## 4. Контейнеризація Docker (ЛР №5)
### Запуск продакшн-збірки (Multi-stage build + PostgreSQL + Volume + Healthcheck)
```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
```
### Запуск у режимі розробки з Hot-Reload (Bind Mounts)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

---

## 5. Балансування навантаження через Nginx (ЛР №6)
### Запуск 3 реплік (`app1`, `app2`, `app3`) за Nginx Load Balancer (:80)
```bash
docker compose -f docker-compose.lb.yml up --build -d
```
### Перевірка Round Robin (18 послідовних запитів)
```bash
python scripts/test_load_balancer.py --url http://localhost:80/health --requests 18
```
### Перевірка відмовостійкості (Failover / Health Check)
```bash
docker compose -f docker-compose.lb.yml stop app2
python scripts/test_load_balancer.py --url http://localhost:80/health --requests 12
docker compose -f docker-compose.lb.yml start app2
```
### Тестування альтернативних алгоритмів (Least Connections / Weighted / IP Hash)
У `docker-compose.lb.yml` замініть рядок монтування конфігурації Nginx на `nginx/nginx.least_conn.conf`, `nginx/nginx.weighted.conf` або `nginx/nginx.ip_hash.conf` та виконайте `docker compose -f docker-compose.lb.yml restart nginx`.
