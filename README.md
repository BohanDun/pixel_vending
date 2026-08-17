# Pixel Vending Simulator

A full-stack pixel-art vending machine simulator built with FastAPI, SQLite,
SQLAlchemy, Alembic, Next.js, and React.

![Pixel Vending Simulator demo](docs/demo.gif)

Users manage products, warehouse inventory, prices, and vending machines while
virtual customers automatically visit the store and make randomized purchases.
The application records transactions, restocks machines after stockouts, and
creates daily sales summaries in the Pacific/Auckland timezone.

## Highlights

- A live pixel-art store where animated customers visit vending machines and
  display their purchase results.
- End-to-end inventory flows across warehouse stock, machine capacity,
  purchases, stockouts, and automatic supplier delivery.
- Operational dashboards covering revenue, transaction outcomes, units sold,
  and top-performing products.
- Authenticated full-stack application with a REST API, relational data model,
  migrations, scheduled jobs, and automated service tests.

## Screenshots

### Live store dashboard

Monitor store activity, inventory totals, revenue, and customer purchases from
the main control room.

![Live Pixel Mart dashboard](docs/dashboard.png)

### Sales reports

Review 30-day sales summaries alongside filterable transaction history.

![Sales reports and transaction history](docs/reports.png)

### Inventory and machine management

Create products and machines, update prices, and move inventory between the
warehouse and individual vending machines.

![Inventory and vending machine management](docs/inventory-management.png)

## Features

### Store management

- Register and sign in with JWT authentication.
- Create products with a name, description, starting quantity, and price.
- Change product prices and manually restock the warehouse.
- Create up to four vending machines.
- Assign products to machines and move stock between machines and the warehouse.
- Pause automatic simulation when inventory is changed manually.

### Customer simulation

- Generate virtual customers with randomized names, budgets, and pixel-art
  appearances.
- Purchase random quantities of one or more products.
- Purchase from multiple vending machines in a single visit.
- Record successful purchases and failures such as insufficient budget and
  out-of-stock products.
- Display customer movement and purchase results in the Pixel Mart scene.

### Inventory automation

- Each machine product slot has a capacity of 50 units.
- Automatic restocking is triggered after an out-of-stock purchase.
- If warehouse stock is insufficient, supplier delivery increases warehouse
  stock before the machine is refilled.
- Inventory changes and purchases are handled through database transactions.

### Sales history

- Keep detailed transaction records for the most recent seven days.
- Keep daily sales summaries for the most recent 30 days.
- Settle the previous day automatically at midnight in Pacific/Auckland time.
- Catch up on missed settlement tasks when the backend starts.
- Display revenue, successful and failed transactions, units sold, and the
  top-selling product.

## Technology

| Area | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite, Alembic |
| Authentication | JWT, python-jose, Passlib, bcrypt |
| Scheduler | APScheduler |
| Frontend | Next.js 15, React 19, Axios, Bootstrap |
| Testing | Python unittest |

## Project structure

```text
pixel_vending/
├── backend/
│   ├── api/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── database.py
│   │   ├── deps.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── alembic.ini
│   └── requirements.txt
├── docs/
│   ├── dashboard.png
│   ├── demo.gif
│   ├── inventory-management.png
│   └── reports.png
├── frontend/
│   ├── public/assets/
│   ├── src/app/
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## Local setup

### Requirements

- Python 3.12
- Node.js and npm

### 1. Create the Python environment

Run this once from the project root:

```bash
cd pixel_vending

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 2. Configure backend environment variables

Copy the provided example, then replace its development secret:

```bash
cp backend/.env.example backend/.env
```

`backend/.env` contains:

```env
AUTH_SECRET_KEY=replace_with_a_long_random_secret
AUTH_ALGORITHM=HS256
```

The `.env` file and local SQLite database are ignored by Git.

### 3. Apply database migrations

```bash
cd backend
source ../.venv/bin/activate
python -m alembic upgrade head
```

### 4. Install frontend dependencies

```bash
cd ../frontend
npm install
```

## Running the application

### Quick start

After completing the local setup, start both servers from the project root:

```bash
./dev.sh
```

The frontend runs at <http://localhost:3000> and the backend API runs at
<http://localhost:8000>. Press `Ctrl+C` to stop both servers.

### Start each server separately

Alternatively, use two terminals.

#### Terminal 1: backend

```bash
cd backend
source ../.venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000
```

Backend:

- API: <http://localhost:8000>
- Swagger documentation: <http://localhost:8000/docs>

#### Terminal 2: frontend

```bash
cd frontend
npm run dev
```

Frontend: <http://localhost:3000>

If Next.js selects port 3001, another process is still using port 3000.

## Tests and checks

### Backend tests

```bash
cd backend
source ../.venv/bin/activate
python -m unittest discover -s tests -v
```

### Database migration check

```bash
python -m alembic check
```

### Frontend production build

Stop the frontend development server before running the build:

```bash
cd frontend
npm run build
```

## Local-development notes

- The frontend currently expects the API at `http://localhost:8000`.
- The backend currently permits CORS requests from `http://localhost:3000`.
- Authentication tokens are stored in browser session storage.
- The application uses `Pacific/Auckland` for daily settlement.
- This repository is intended as a learning and portfolio project.
