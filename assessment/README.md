# FastAPI Microservices Assessment

This repository contains two independent, production-ready microservices built with FastAPI:
1. **Auth Service**: Handles user management, JWT issuance, and Role-Based Access Control (RBAC).
2. **Product Service**: Handles CRUD operations for Products and Categories, with caching and stock management.

## 🏗️ Architecture & Decisions
- **Microservices Pattern**: The system is split into two independent services. They communicate completely statelessly via JWT tokens. The Product Service verifies tokens issued by the Auth Service without needing to query the Auth DB.
- **Database-per-Service**: Each service has its own independent PostgreSQL database instance (`auth_db` and `product_db`), adhering strictly to microservice decoupling principles.
- **Caching & Rate Limiting**: Redis is used in both services. In the Auth Service, it powers endpoint rate-limiting. In the Product Service, it caches product detail lookups and supports invalidation on updates/deletions.
- **Strict Typing**: Full Python 3.11+ strict typing is enforced using MyPy, and SQLAlchemy 2.0 `Mapped` schemas are used for all database models.
- **Soft Deletion**: Products use an `is_active` boolean rather than hard-deleting rows, ensuring historical data is preserved.
- **Atomic Operations**: Stock modifications utilize atomic database updates (e.g., `Product.stock_quantity = Product.stock_quantity + delta`) to prevent race conditions during concurrent checkouts.

## 💻 Tech Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via `asyncpg` & SQLAlchemy 2.0)
- **Cache**: Redis (via `redis.asyncio`)
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest, Pytest-Asyncio, HTTPX, AIOSQLite, FakeRedis

---

## 🚀 Setup & Execution

### 1. Start the Services
The entire infrastructure (PostgreSQL databases, Redis cache, and both FastAPI APIs) is managed via Docker Compose.

```bash
docker compose up -d --build
```

### 2. Access the APIs
Once running, the services will be available at:
- **Auth Service**: `http://localhost:8001` (Docs: `http://localhost:8001/docs`)
- **Product Service**: `http://localhost:8002` (Docs: `http://localhost:8002/docs`)

---

## 🧪 Testing & Code Quality

Both services have fully isolated test suites that utilize in-memory SQLite and FakeRedis, meaning they execute incredibly fast (under 1 second) and don't require standing up real Docker dependencies during CI/CD pipelines.

### Run Unit & Integration Tests (with Coverage)
```bash
# Test Auth Service
docker compose run --rm auth-service pytest --cov=app -v

# Test Product Service
docker compose run --rm product-service pytest --cov=app -v
```

### Run Strict Type Checking
```bash
# Check Auth Service
docker compose run --rm auth-service mypy app tests

# Check Product Service
docker compose run --rm product-service mypy app tests
```

### Run Linter (Ruff)
```bash
docker compose run --rm auth-service ruff check app tests
docker compose run --rm product-service ruff check app tests
```

---

## 🔑 Core API Endpoints

### Auth Service (Port 8001)
- `POST /auth/register`: Create a new user (default role: `customer`)
- `POST /auth/login`: Authenticate and receive `access_token` and `refresh_token`
- `GET /auth/me`: Get current authenticated user details
- `POST /auth/refresh`: Refresh an expired access token
- `PATCH /users/{id}/role`: (Admin only) Promote/demote a user's role

### Product Service (Port 8002)
- `POST /categories`: (Admin only) Create a new category
- `POST /products`: (Admin only) Create a new product
- `GET /products/{id}`: Get product by ID (Cached in Redis)
- `PUT /products/{id}`: (Admin only) Update product details and invalidate cache
- `PATCH /products/{id}/stock`: (Admin only) Atomically increment/decrement stock
- `DELETE /products/{id}`: (Admin only) Soft-delete a product
