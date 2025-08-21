# DeepMD AI Services

Django backend service for DeepMD AI applications.

## Deployment to Zeabur

### Prerequisites

1. Create account on [Zeabur](https://zeabur.com)
2. Fork/clone this repository

### Database Setup

1. In Zeabur dashboard, add a PostgreSQL service to your project
2. Get the database connection string from Zeabur dashboard

### Environment Variables

Set the following environment variables in Zeabur:

```bash
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=your-app-name.zeabur.app
DATABASE_URL=postgresql://user:password@host:port/dbname
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### Deploy Steps

1. Connect your GitHub repository to Zeabur
2. Add PostgreSQL service
3. Configure environment variables
4. Deploy the Django service
5. The application will automatically:
   - Install dependencies from `pyproject.toml`
   - Run database migrations
   - Collect static files
   - Start with Gunicorn

## Local Development

1. Install dependencies:
```bash
pip install -e .
```

2. Create `.env` file based on `.env.example`

3. Run migrations:
```bash
cd deepmd_ai_services
python manage.py migrate
```

4. Start development server:
```bash
python manage.py runserver
```

## Project Structure

```
deepmd-ai-services/
├── deepmd_ai_services/          # Django project directory
│   ├── deepmd_ai_services/      # Django settings package
│   │   ├── settings.py          # Main settings
│   │   ├── urls.py              # URL routing
│   │   └── wsgi.py              # WSGI configuration
│   └── manage.py                # Django management script
├── pyproject.toml               # Python dependencies and build config
├── zbpack.json                  # Zeabur build configuration
├── .env.example                 # Environment variables template
└── README.md                    # This file
```
