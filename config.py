import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///multi_agent_system.db')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Agent Configuration
    MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '4000'))
    AGENT_TIMEOUT = int(os.getenv('AGENT_TIMEOUT', '30'))
    
    # Multi-user support
    MAX_CONCURRENT_USERS = int(os.getenv('MAX_CONCURRENT_USERS', '100'))
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour
