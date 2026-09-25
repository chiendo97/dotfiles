---
name: scaffold
description: |
  Scaffold a new Litestar web project with the full standard stack:
  Litestar + SQLModel + HTMX + Pico CSS + Casbin ReBAC + JWT auth + async everything.
  Includes CI/CD (GitLab), Makefile, Dockerfile, linting (ruff + basedpyright),
  testing (pytest), Claude agents, and /gen-test skill.
  Use when starting a new web project, e.g. "/scaffold", "new project", "init project".
---

# Scaffold

One-command project scaffold: empty directory → fully wired Litestar async web app.

## Arguments

`/scaffold <project_name>` — optional. If not provided, ask the user for:
- **Project name** (kebab-case, used for pyproject.toml and directory)
- **Git remote** (optional, e.g. `git@git.urieljsc.com:group/repo.git`)

If the user provides arguments, parse them: `/scaffold zariel` or `/scaffold zariel git@git.urieljsc.com:zariel/navis.git`

## Step 1: Initialize

```bash
uv init --name <project_name>
uv add litestar uvicorn jinja2 sqlmodel httpx 'python-jose[cryptography]' bcrypt python-multipart casbin pyjwt aiosqlite
uv add --dev ruff basedpyright pytest pytest-asyncio httpx
mkdir -p templates/fragments static tests/e2e .claude/agents .claude/skills docs
```

## Step 2: Create pyproject.toml config

Append these tool configs to `pyproject.toml` (after the dependency sections):

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.basedpyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
reportExplicitAny = false
reportAny = false
reportAssignmentType = "warning"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Step 3: Create source files

### db.py — async engine + session factory

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# TODO: load from env / config
DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL, echo=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

### models.py — base models (User only, user extends per project)

```python
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True)
    name: str = Field(max_length=255)
    password_hash: str = Field(max_length=255)
```

### auth.py — JWT + bcrypt + Litestar DI provider

```python
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User

# TODO: load from env / config
SECRET_KEY = "change-me-before-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError):
        return None


async def provide_current_user(session: AsyncSession, connection: ASGIConnection) -> User:
    auth_header = connection.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise NotAuthorizedException(detail="Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ")
    user_id = decode_token(token)
    if user_id is None:
        raise NotAuthorizedException(detail="Invalid token")

    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        raise NotAuthorizedException(detail="User not found")
    return user
```

### authz.py — Casbin ReBAC (empty check_access, user wires per project)

```python
import casbin


_enforcer: casbin.Enforcer | None = None


def get_enforcer() -> casbin.Enforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = casbin.Enforcer("casbin_model.conf", "casbin_policy.csv")
    return _enforcer


def provide_enforcer() -> casbin.Enforcer:
    return get_enforcer()
```

### casbin_model.conf

```
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && (p.obj == "*" || r.obj == p.obj) && r.act == p.act
```

### casbin_policy.csv — empty starter, user fills per project

```
p, admin, *, view
p, admin, *, create
p, admin, *, edit
p, admin, *, delete

p, viewer, *, view
```

### app.py — Litestar app with DI wired

```python
from pathlib import Path

import casbin
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.di import Provide
from litestar.static_files import StaticFilesConfig
from litestar.template import TemplateConfig

from auth import provide_current_user
from authz import provide_enforcer
from db import get_session, init_db


async def on_startup() -> None:
    await init_db()


app = Litestar(
    route_handlers=[],  # TODO: add route handlers
    on_startup=[on_startup],
    dependencies={
        "session": Provide(get_session),
        "current_user": Provide(provide_current_user),
        "enforcer": Provide(provide_enforcer, sync_to_thread=False),
    },
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[
        StaticFilesConfig(directories=[Path("static")], path="/static"),
    ],
)
```

### templates/base.html

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}App{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="container">
        <ul>
            <li><strong>{% block brand %}App{% endblock %}</strong></li>
        </ul>
        <ul>
            {% block nav %}{% endblock %}
        </ul>
    </nav>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

## Step 4: Create test scaffolding

### tests/__init__.py — empty

### tests/conftest.py

```python
import pytest
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app import app


@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield e
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await e.dispose()


@pytest.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture
async def client(session):
    async def override_get_session():
        yield session

    app.dependencies["session"] = override_get_session
    async with AsyncTestClient(app=app) as c:
        yield c
```

### tests/test_auth.py — basic smoke tests

```python
from auth import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token(user_id=42)
    user_id = decode_token(token)
    assert user_id == 42


def test_decode_invalid_token():
    assert decode_token("garbage.token.here") is None
```

## Step 5: Create build files

### Makefile

```makefile
.PHONY: install lint format typecheck test build dev clean

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run basedpyright

test:
	uv run pytest -v

check: lint typecheck test

dev:
	uv run uvicorn app:app --reload --port 8000

build:
	docker build -t <project_name> .

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache *.db
```

Replace `<project_name>` with the actual project name.

### Dockerfile

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=builder /app /app

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .gitlab-ci.yml

```yaml
stages:
  - check
  - test
  - build

variables:
  UV_CACHE_DIR: .uv-cache

default:
  image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
  cache:
    key: uv-$CI_COMMIT_REF_SLUG
    paths:
      - .uv-cache
      - .venv
  before_script:
    - uv sync

lint:
  stage: check
  script:
    - uv run ruff check .

typecheck:
  stage: check
  script:
    - uv run basedpyright

test:
  stage: test
  script:
    - uv run pytest -v
  needs:
    - lint
    - typecheck

build:
  stage: build
  image: docker:27
  services:
    - docker:27-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  before_script: []
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .
    - docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:latest
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
    - docker push $CI_REGISTRY_IMAGE:latest
  only:
    - main
    - master
```

### .gitignore

```
# Python
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info

# Virtual environments
.venv

# Database
*.db

# Uploaded files
uploads/

# Environment
.env

# IDE
.idea/
.vscode/

# Screenshots / temp files
*.jpeg
*.jpg
*.png
```

## Step 6: Create Claude agents and skills

Copy the standard agent and skill files. These are the same across projects (adapted from the navis/sqms pattern):

### Agents to create in `.claude/agents/`:

1. **analyzer.md** — codebase analysis (sonnet, read-only tools)
2. **planner.md** — implementation planning (sonnet, read-only tools)
3. **implementer.md** — code execution (sonnet, full tools)
4. **pipeline.md** — orchestrates analyze → plan → implement (uses Agent tool)
5. **test-analyzer.md** — analyzes routes, produces test plan (sonnet, read-only)
6. **test-generator.md** — generates pytest files from test plan (sonnet, write tools)
7. **test-runner.md** — runs tests, structured report (haiku, bash only)

### Skill to create in `.claude/skills/`:

1. **gen-test.md** — `/gen-test <source_path>` full E2E test generation flow

**Source for these files**: read the agents and skills from `/home/cle/Source/navis/.claude/` and copy them. The test-analyzer and test-generator agents reference Litestar + SQLModel + HTMX patterns — keep as-is since this scaffold is for the same stack.

## Step 7: Create CLAUDE.md

Write a `CLAUDE.md` with:
- Project name and one-line description (ask user if not obvious)
- Stack summary (Litestar + SQLModel + HTMX + Pico CSS + Casbin)
- Pointer to TECHNICAL.md for details

## Step 8: Verify

Run in sequence:
1. `uv run ruff check .` — lint passes
2. `uv run basedpyright` — type check (warnings OK, 0 errors)
3. `uv run pytest -v` — tests pass
4. Start the server briefly to verify it boots: `uv run uvicorn app:app --port 8000 &` then `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/schema` then kill

Report results to the user.

## Step 9: Git init + push (if remote provided)

```bash
git init
git add .gitignore CLAUDE.md Makefile Dockerfile .gitlab-ci.yml \
  app.py auth.py authz.py db.py models.py pyproject.toml uv.lock \
  casbin_model.conf casbin_policy.csv \
  templates/ tests/ .claude/ docs/
git commit -m "Initial scaffold: Litestar + SQLModel + HTMX + Casbin

Co-Authored-By: Claude <noreply@anthropic.com>"
```

If a git remote was provided:
```bash
git remote add origin <remote_url>
git push -u origin master
```

Tell the user the project is ready and list what was created.
