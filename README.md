# Kaargoosha FastAPI Backend

A FastAPI + SQLAlchemy backend service for family microfinance: user management, loan processing, deposits, installment payments, and permission system.

**Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0, Alembic, RabbitMQ, SQLite/PostgreSQL

## Features

### User Management
- User creation, authentication, phone verification
- Social media platform tracking (web, mobile, Bale)
- Chat ID mapping for Bale bot notifications
- User roles and permission system

### Loan Processing
- Loan request creation with duration validation
- Loan approval with fund pool balance checks
- Eligibility: user balance must meet threshold
- Installment generation (monthly payments)
- Loan rejection with reason tracking

### Financial Operations
- **Account Management** — wallet balance, credit/debit operations
- **Transactions** — unified ledger for deposits, loans, installments
- **Deposits** — proof-based wallet charging with approval workflow
- **Installments** — payment proof submission, tracking, collection

### Notifications
- Admin notifications for pending loans, deposits, installments
- Member notifications for approvals/rejections
- Permission-based recipient filtering

### Administration
- Role creation and management
- Permission assignment to roles
- User role assignment/revocation
- Balance threshold configuration

## Quick Start

### Prerequisites

```
python 3.10+
PostgreSQL or SQLite (default: sqlite:///./sqlite.db)
RabbitMQ (localhost:5672)
```

### Installation

```bash
cd Kaargoosha-FastAPI
pip install -r requirements.txt

# Create .env
cat > .env << EOF
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
ALEMBIC_DATABASE_URL=postgresql://user:password@localhost/kaargoosha
# or SQLite:
ALEMBIC_DATABASE_URL=sqlite:///./sqlite.db
GOD=god_user_id
LOAN_MAX_AMOUNT=50000000
EOF

# Run migrations
alembic upgrade head

# Start consumer
python -m account.consumer
python -m loan.consumer
```

### Services Running

Each consumer listens to RabbitMQ exchanges and processes messages:

```bash
# Terminal 1: Account consumer
python -m account.consumer

# Terminal 2: Loan consumer  
python -m loan.consumer

# Terminal 3: Optional - FastAPI API server (if needed)
uvicorn main:app --reload
```

## Architecture

```
Bale Bot (RabbitMQ Publisher)
    ↓ (RPC with correlation_id)
    ↑ (Response via reply_to queue)
RabbitMQ (Broker)
    ├─ Exchanges (topic)
    │  ├─ user, loan, account
    │  ├─ deposit, installment_payment
    │  └─ notify
    ├─ Queues (per service)
    └─ Routing (topic patterns)
    ↓
FastAPI Consumer Services
    ├─ account/consumer.py
    ├─ loan/consumer.py
    └─ user_management/consumer.py
    ↓
SQLAlchemy ORM
    ↓
Database (SQLite/PostgreSQL)
```

## Documentation

- 📖 [`docs/MODELS.md`](docs/MODELS.md) — Database schema & relationships
- 🔄 [`docs/SERVICES.md`](docs/SERVICES.md) — Service layer architecture
- 📨 [`docs/MESSAGE_FLOW.md`](docs/MESSAGE_FLOW.md) — RabbitMQ routing & RPC patterns
- 📊 [`docs/database_schema_diagram.svg`](docs/database_schema_diagram.svg) — Visual schema
- 🔗 [`docs/service_dependency_diagram.svg`](docs/service_dependency_diagram.svg) — Service interactions

## Project Structure

```
account/
├── models.py       # Account, Transaction, Deposit, DepositRequest, AccountSetting
├── service.py      # AccountService, BankInfoService, DepositService
├── consumer.py     # account.*, bank_info.*, deposit.* routing
└── schema.py       # Response schemas

loan/
├── models.py       # Loan, Installment, FundPool, InstallmentPaymentRequest
├── service.py      # LoanService, InstallmentService, InstallmentPaymentService
├── consumer.py     # loan.*, installment_payment.* routing
└── schema.py

user_management/
├── models.py       # UserModel, UserSocialMediaID, UserRole, RolePermission
├── service.py      # UserService, RoleService, PermissionService
├── consumer.py     # user.*, role.*, permission.* routing
└── permissions.py  # @permission decorator

core/
├── database.py     # SQLAlchemy setup, session management
├── rabbitmq_connection.py  # RabbitMQ connection pool
├── settings.py     # Configuration, logging
└── notification_publisher.py  # Send notifications to Bale bot

migrations/
└── versions/       # Alembic schema versions

main.py            # Optional: FastAPI app (if REST API needed)
```

## Key Concepts

### Services Layer

Each service encapsulates business logic and queries:
```python
class LoanService:
    def create(self, data: dict) -> str:
        """Return JSON response"""
    
    def approve(self, data: dict) -> str:
        """Requires @permission decorator"""
    
    def reject(self, data: dict) -> str:
        """Requires @permission decorator"""
```

### Consumer Pattern

Each exchange has a consumer that routes to services:
```python
# loan/consumer.py
if method.routing_key == 'loan.create':
    result = LoanService().create(data)
elif method.routing_key == 'loan.approve':
    result = LoanService().approve(data)  # @permission checked
```

### Permission System

Backend validates permissions via decorator:
```python
from user_management.permissions import permission, Permissions

@permission(Permissions.LOAN_APPROVE)
def approve(self, data: dict):
    # Only called if user (data["requested_by"]) has LOAN_APPROVE
    pass
```

### RPC Pattern

Bot sends request with callback queue:
1. Bot publishes to `exchange` with `reply_to`, `correlation_id`
2. Consumer processes, publishes response to `reply_to`
3. Bot receives response, matches `correlation_id`
4. Bot async callback with response data

### Transactions Model

Unified financial ledger:
```python
class TransactionType(enum):
    deposit = "deposit"
    loan_disbursement = "loan_disbursement"
    installment_payment = "installment_payment"

class TransactionDirection(enum):
    credit = "credit"  # money in
    debit = "debit"    # money out

# Every financial operation writes here
Transaction(
    user_id=123,
    amount=5000000,
    direction=TransactionDirection.credit,
    type=TransactionType.loan_disbursement,
    reference_type="loan",
    reference_id=42
)
```

## RabbitMQ Exchanges

| Exchange | Type | Routing Keys | Producer | Consumer |
| --- | --- | --- | --- | --- |
| `user` | topic | `user.create`, `user.check_phone_number`, `user.get_user_by_username`, etc | Bot/User Service | User Consumer |
| `loan` | topic | `loan.create`, `loan.approve`, `loan.reject`, `loan.get_loans` | Bot/Loan Service | Loan Consumer |
| `account` | topic | `account.get_balance`, `account.set_threshold` | Account Service | Account Consumer |
| `deposit` | topic | `deposit.create`, `deposit.approve`, `deposit.reject` | Bot/Deposit Service | Account Consumer |
| `bank_info` | topic | `bank_info.get`, `bank_info.save` | Bot/Bank Service | Account Consumer |
| `installment_payment` | topic | `installment_payment.get_pending`, `installment_payment.create`, `installment_payment.approve` | Bot/Installment Service | Loan Consumer |
| `notify` | topic | `notify.loan_request`, `notify.loan_approved`, `notify.deposit_request`, etc | Services | Bot Consumer |

## Database Models

### Core Models
- **UserModel** — users table with names, phone, social media
- **Account** — wallet balance per user
- **Transaction** — unified financial ledger
- **FundPool** — shared pool balance for loans

### Loan Models
- **Loan** — loan requests with status, amount, duration
- **Installment** — monthly payments with due dates, paid_at
- **InstallmentPaymentRequest** — proof submission & approval

### Deposit Models
- **DepositRequest** — wallet charging with proof & approval
- **AccountSetting** — configurable loan balance threshold

### User Management
- **UserSocialMediaID** — platform accounts (web, mobile, Bale)
- **UserRole** — user → role assignment
- **Role** — named roles
- **Permission** — permission records
- **RolePermission** — role → permission assignment

### Bank Info
- **UserBankInfo** — card number, IBAN per user

See [`docs/MODELS.md`](docs/MODELS.md) for full schema with relationships.

## Migrations

Run Alembic to manage schema changes:

```bash
# Create migration after model change
alembic revision --autogenerate -m "Add new column"

# Review migration file, then:
alembic upgrade head
```

Each migration chains from the previous revision with `down_revision` field.

## Error Handling

**Service Methods:**
- Return JSON string with `{"error": "message"}` on failure
- Return JSON string with data dict on success

**Validation Errors:**
- Phone number format → `{"error": "Invalid phone number"}`
- Loan eligibility → `{"error": "insufficient_balance", "balance": 100000, "required": 500000}`
- Permission denied → `{"error": "insufficient permissions"}`

**Database Errors:**
- Rollback on exception, log traceback, return error JSON

## Testing

```bash
pytest tests/
```

Requires running RabbitMQ + FastAPI (if integration tests).

## Deployment

### Environment Variables

```
RABBITMQ_HOST=rabbitmq.example.com
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=user
RABBITMQ_PASSWORD=pass
ALEMBIC_DATABASE_URL=postgresql://user:pass@db:5432/kaargoosha
GOD=1  # System admin user ID for initialization
LOAN_MAX_AMOUNT=50000000  # Max loan amount in smallest currency unit
```

### Running Consumers

```bash
# Start consumer processes (production: use systemd/docker)
python -m account.consumer
python -m loan.consumer
```

## Contributing

1. Follow service layer pattern (models → service → consumer)
2. Use `@permission` decorator for admin operations
3. Return JSON dicts from services (serialized by consumer)
4. Write Alembic migration for any schema changes
5. Log errors with `logger.error(traceback.format_exc())`
6. Update docs/ when adding new exchanges or major services

## License

Proprietary — Family Microfinance Project
