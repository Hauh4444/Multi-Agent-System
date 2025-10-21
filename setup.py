#!/usr/bin/env python3
"""
Setup script for Multi-Agent System
This script sets up the development environment and installs dependencies.
"""

import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print setup banner."""
    print("=" * 60)
    print("🤖 Multi-Agent System Setup")
    print("=" * 60)
    print("Setting up your multi-agent system with Google ADK principles")
    print("=" * 60)

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment."""
    print("🔧 Creating virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def get_activation_command():
    """Get the correct activation command for the platform."""
    if platform.system() == "Windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    # Determine the correct pip command
    if platform.system() == "Windows":
        pip_cmd = "venv\\Scripts\\pip"
    else:
        pip_cmd = "venv/bin/pip"
    
    try:
        # Upgrade pip first
        subprocess.run([pip_cmd, "install", "--upgrade", "pip"], check=True)
        
        # Install requirements
        subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories."""
    print("📁 Creating directories...")
    
    directories = [
        "static/css",
        "static/js",
        "templates",
        "agents",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_env_file():
    """Create .env file with default configuration."""
    print("🔧 Creating environment configuration...")
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    env_content = """# Google AI API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# OpenAI API Configuration (for fallback)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///multi_agent_system.db

# Redis Configuration (for session management)
REDIS_URL=redis://localhost:6379/0

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=demo-secret-key-change-in-production

# Agent Configuration
MAX_CONTEXT_LENGTH=4000
AGENT_TIMEOUT=30
MAX_CONCURRENT_USERS=100
SESSION_TIMEOUT=3600
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file")
    return True

def show_next_steps():
    """Show next steps to the user."""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    print("Next steps:")
    print("1. Activate the virtual environment:")
    print(f"   {get_activation_command()}")
    print("2. Set up your Google AI API key in .env file")
    print("3. Run the demo:")
    print("   python run_demo.py")
    print("4. Or start the system directly:")
    print("   python app.py")
    print("=" * 60)
    print("📚 Documentation:")
    print("   • README.md - Complete setup guide")
    print("   • ARCHITECTURE.md - Technical architecture")
    print("   • demo_script.md - Demo instructions")
    print("=" * 60)

def main():
    """Main setup function."""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
