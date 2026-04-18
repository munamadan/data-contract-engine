# Data Contract Engine

> Automated data quality enforcement through contract-based validation, versioning, and monitoring

[![Tests](https://github.com/yourusername/data-contract-engine/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/data-contract-engine/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/yourusername/data-contract-engine/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/data-contract-engine)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **YAML-based Contract Definitions**: Human-readable data contracts with schema and quality rules
- **Real-time Validation**: Single record validation with detailed error reporting
- **Batch Processing**: Efficient file validation for CSV, JSON, and JSONL formats
- **Semantic Versioning**: Git-like versioning with automatic semantic version bumping
- **Breaking Change Detection**: Automatic identification of breaking vs. non-breaking changes
- **Quality Metrics Dashboard**: Visual analytics for pass rates, trends, and error patterns
- **RESTful API**: Comprehensive API for integration with data pipelines
- **Streamlit UI**: Web interface for contract management and validation

## Tech Stack

**Backend**:
- Python 3.11+
- FastAPI - Modern async web framework
- PostgreSQL - Relational database with JSONB support
- SQLAlchemy - ORM with async support
- Alembic - Database migrations
- Pydantic - Data validation and settings

**Frontend**:
- Streamlit - Python web framework
- Plotly - Interactive visualizations
- Pandas - Data processing

**DevOps**:
- Docker - Containerization
- GitHub Actions - CI/CD
- pytest - Testing framework
- Black - Code formatting
- Ruff - Fast Python linter
- mypy - Static type checking

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/data-contract-engine.git
cd data-contract-engine

# Start PostgreSQL database
docker-compose up -d

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload

# Start frontend (in a new terminal)
cd frontend
streamlit run streamlit_app.py
```

### Access Points

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:8501
- **Database**: localhost:5432
- **pgAdmin**: http://localhost:5050 (admin@dce.local / admin)

## Usage

### Create a Contract

```yaml
contract_version: "1.0"
domain: "user-analytics"
description: "User signup events"

schema:
  user_id:
    type: string
    required: true
    pattern: "^usr_\\d+$"
  
  email:
    type: string
    format: email
    required: true
  
  age:
    type: integer
    min: 18
    max: 120
    required: false

quality_rules:
  freshness:
    max_latency_hours: 2
  
  completeness:
    min_row_count: 1000
    max_null_percentage: 5.0
```

### Validate Data via API

```bash
curl -X POST http://localhost:8000/api/v1/validate/{contract_id} \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "user_id": "usr_12345",
      "email": "test@example.com",
      "age": 25
    }
  }'
```

### Validate Batch Files

```bash
curl -X POST http://localhost:8000/api/v1/validate/{contract_id}/upload \
  -F "file=@data.csv"
```

## Project Structure

```
data-contract-engine/
├── app/                    # Backend application
│   ├── api/               # API endpoints
│   ├── core/              # Business logic
│   ├── models/            # Database & Pydantic models
│   └── utils/             # Utilities
├── frontend/              # Streamlit UI
│   ├── pages/            # Multi-page app
│   └── components/       # Reusable components
├── tests/                # Test suite
├── alembic/             # Database migrations
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## API Documentation

Full API documentation is available at `/docs` when running the server, or in [docs/api.md](docs/api.md).

Key endpoints:

- `POST /api/v1/contracts` - Create contract
- `GET /api/v1/contracts` - List contracts
- `POST /api/v1/validate/{id}` - Validate single record
- `POST /api/v1/validate/{id}/batch` - Batch validation
- `GET /api/v1/metrics/{id}/daily` - Daily metrics
- `GET /api/v1/contract-versions/{id}/versions` - Version history

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_validation_engine.py

# Run with verbose output
pytest -v

# Run linter
ruff check app tests

# Format code
black app tests

# Type check
mypy app
```

## Deployment

### Production Deployment with Docker

```bash
# Build Docker image
docker build -t data-contract-engine .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  data-contract-engine
```

### Cloud Deployment

**Backend (Render.com)**:
1. Connect GitHub repository
2. Create Web Service with Docker
3. Set `DATABASE_URL` environment variable
4. Deploy

**Frontend (Streamlit Cloud)**:
1. Connect GitHub repository
2. Select `frontend/streamlit_app.py`
3. Set `API_BASE_URL` in secrets
4. Deploy

See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions.

## Documentation

- [Architecture](docs/architecture.md) - System design and architecture
- [API Documentation](docs/api.md) - Complete API reference
- [Contract Specification](docs/contract-spec.md) - Contract definition language
- [Deployment Guide](docs/deployment.md) - Production deployment instructions

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Custom validators (Python functions)
- [ ] Parquet file support
- [ ] Webhook notifications
- [ ] GraphQL API
- [ ] Multi-tenant support
- [ ] Real-time validation with WebSocket

## Acknowledgments

Built with inspiration from industry data contract solutions:
- [Data Contracts](https://www.datacontract.com/)
- [Great Expectations](https://greatexpectations.io/)
- [Soda](https://www.soda.io/)

## Contact

- GitHub Issues: [Report bugs](https://github.com/munamadan/data-contract-engine/issues)
- Email: dipankharel@gmaik.com
