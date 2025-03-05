# Forgeo Backend

Backend service for Forgeo, a HubSpot data auditing SaaS platform.

## Features

- FastAPI-based REST API
- PostgreSQL database
- HubSpot OAuth integration
- CrewAI-powered data analysis
- Docker containerization
- Secure authentication and authorization

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL
- HubSpot Developer Account

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/yourusername/forgeo-backend.git
cd forgeo-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run with Docker:
```bash
docker-compose up -d
```

The API will be available at http://localhost:8000

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
forgeo-backend/
├── app/
│   ├── core/          # Core functionality
│   ├── api/           # API endpoints
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── tests/         # Test suite
├── docker/           # Docker configuration
├── alembic/          # Database migrations
└── requirements.txt  # Python dependencies
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 