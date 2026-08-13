# Database Setup & Alembic Migrations

This project uses SQLAlchemy 2.0 and Alembic for database ORM and migrations.

## Environment Setup

Ensure your `.env` file contains your database connection string:

```env
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE
```

## Alembic Commands

- **Apply all pending migrations to database**:
  ```bash
  uv run alembic upgrade head
  ```

- **Generate a new migration when models change**:
  ```bash
  uv run alembic revision --autogenerate -m "your migration message"
  ```

- **Check current database migration version**:
  ```bash
  uv run alembic current
  ```

- **Verify if schema matches models (no pending changes)**:
  ```bash
  uv run alembic check
  ```

- **Roll back the latest migration**:
  ```bash
  uv run alembic downgrade -1
  ```
