# steps of creating this project - quick rough

## 1. inital project setup - folder files uv venv

- created the folder structure and initial files

```
todo-app/
├── app/
│   ├── api/v1/endpoints/    # REST API endpoints
│   ├── core/                # Security & logging
│   ├── db/repositories/     # Data access layer
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic validation
│   ├── services/            # Business logic
│   └── middleware/          # Custom middleware
├── alembic/                 # Database migrations
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-container setup
└── requirements.txt         # Dependencies
```

- INITIALIZE UV / PROJECT VENV / DEPENDENCIES

  - cd into the project directory and select your python version example

    ```bash
        pyenv local 3.11.8
    ```

  - initialize the uv project

    ```bash
    uv init
    ```

  - add project dependencies and after that the .venv will be created

    ```bash
    uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic python-dotenv
    ```

  - activate venv

    ```bash
    source .venv/bin/activate
    ```

  - verify with

    ```bash
    uv pip list
    ```

  - for vs code select python interpreter -> `ctrl + shift + p` and type `Python: Select Interpreter` and enter the full path like this `/home/user/Desktop/dev/backend/WebDevLearning/todo-app/.venv/bin/python`

  - run via

    ```
    uv run uvicorn app.main:app --reload
    ```

  - can also see pyproject.toml for the dependencies list

  - Export for Docker

    When you later build Docker images, it’s cleaner to use a `requirements.txt` inside Docker.  
    `uv` can generate that automatically:

    ```
    uv export --frozen > requirements.txt
    ```

    Then in Dockerfile, you’ll use:

    ```dockerfile
     COPY requirements.txt .
     RUN pip install --no-cache-dir -r requirements.txt
    ```

## 2. Docker Setup & Commands

- **Create Dockerfile**

  - Multi-stage build for smaller final image
  - Install system dependencies (Postgres client, gcc)
  - Create virtual environment and install Python dependencies
  - Copy app code and switch to non-root user
  - Expose port `8000` and set healthcheck

- **Create docker-compose.yml**

  - Define 3 services: `db` (Postgres), `app` (FastAPI), `pgadmin` (optional)
  - Add volumes for persistent storage (`postgres_data`)
  - Create network (`todo_network`) for container communication
  - Use `depends_on + healthcheck` to ensure FastAPI waits for Postgres

- **Create .env file**

  - Store DB credentials, secrets, API configs, ports
  - Example:

    ```
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=todo_app
    SECRET_KEY=...
    DEBUG=True
    ```

- **Build and run containers**

  ```bash
  docker compose up --build
  ```

- **Check running containers**

  ```bash
  docker compose ps
  ```

- **View logs**

  ```bash
  docker compose logs -f app
  docker compose logs -f db
  ```

- **Stop containers**

  ```bash
  docker compose down
  ```

- **Connect to Postgres from host / DBeaver**

  - Host: `localhost`
  - Port: `5433`
  - User: `postgres`
  - Password: `postgres`
  - DB: `todo_app`

- **Connect to pgAdmin**

  - Open `http://localhost:5055`
  - Login: `admin@admin.com` / `admin`
  - Add new server: Host = `db`, Port = `5433`, Username / Password from .env

- **Connect via terminal**

  ```bash
  psql -h localhost -p 5433 -U postgres -d todo_app
  ```

  and use password - `postgres`

- **Test FastAPI**

  - Browser / Postman: `http://localhost:8000/health` → should return `{"status": "ok"}`

- **Optional: wait-for-db script**

  - Ensure FastAPI waits until Postgres is ready before starting
  - Can be added in Dockerfile / docker-compose command

---
