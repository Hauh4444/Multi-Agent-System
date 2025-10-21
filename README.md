# Multi-Agent System

A sophisticated multi-agent AI system built with Flask, featuring specialized agents for conversational AI, memory management, and intelligent matching. The system demonstrates advanced orchestration patterns and real-time communication capabilities.

## Architecture

The system implements a distributed agent architecture with the following components:

- **AI Orchestrator**: Central coordination hub managing agent interactions and workflow
- **Conversational Agent**: Handles natural language processing, sentiment analysis, and response generation
- **Memory Agent**: Manages session data, user preferences, and conversation history
- **Matching Agent**: Processes user inputs for intent analysis and entity extraction

## Features

- **Real-time Communication**: WebSocket-based chat interface with instant responses
- **Multi-user Support**: Concurrent session management with isolated contexts
- **AI Integration**: Dual AI provider support (Google AI with OpenAI fallback)
- **Intelligent Fallbacks**: Robust error handling with graceful degradation
- **Modern UI**: Responsive, accessible interface with real-time status updates
- **Comprehensive Testing**: 68 unit and integration tests with full coverage

## Technology Stack

- **Backend**: Flask, Flask-SocketIO, SQLite
- **AI Providers**: Google AI (Gemini), OpenAI (GPT-3.5-turbo)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Testing**: pytest with async support and mocking
- **Dependencies**: Python 3.12+

## Quick Start

### Prerequisites

- Python 3.12 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Multi-Agent-System
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Environment Configuration

Create a `.env` file with the following variables:

```env
# AI Provider API Keys
GOOGLE_API_KEY=your_google_ai_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
SECRET_KEY=your_secure_secret_key_here
FLASK_ENV=development
FLASK_DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///multi_agent_system.db
REDIS_URL=redis://localhost:6379/0

# System Limits
MAX_CONTEXT_LENGTH=4000
AGENT_TIMEOUT=30
MAX_CONCURRENT_USERS=100
SESSION_TIMEOUT=3600
```

### API Keys Setup

**Google AI API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new project or select existing
3. Generate an API key
4. Add to your `.env` file

**OpenAI API Key:**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Generate a new secret key
5. Add to your `.env` file

### Running the Application

1. Start the development server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Start chatting with the multi-agent system!

## Testing

The project includes comprehensive test coverage with 68 tests covering all major functionality:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=agents --cov=orchestrator --cov=app

# Run specific test categories
python -m pytest tests/test_conversational_agent.py -v
python -m pytest tests/test_integration.py -v
```

### Test Categories

- **Unit Tests**: Individual component testing with mocked dependencies
- **Integration Tests**: End-to-end system testing
- **Agent Tests**: Specialized testing for each agent type
- **Orchestrator Tests**: Central coordination testing

## System Architecture

### Agent Communication Flow

```
User Input → AI Orchestrator → Memory Agent → Matching Agent → Conversational Agent → Response
```

### Data Flow

1. **Input Processing**: User message received via WebSocket
2. **Session Management**: Memory agent retrieves user context
3. **Intent Analysis**: Matching agent processes intent and entities
4. **Response Generation**: Conversational agent creates contextual response
5. **Context Update**: Memory agent stores conversation history
6. **Real-time Delivery**: Response sent back to user

### Error Handling

The system implements multiple layers of error handling:

- **API Failures**: Automatic fallback from Google AI to OpenAI
- **Rate Limiting**: Intelligent request throttling
- **Network Issues**: Retry mechanisms with exponential backoff
- **Graceful Degradation**: System continues functioning with reduced capabilities

## API Endpoints

### WebSocket Events

- `connect`: Establish connection
- `join_session`: Join user session
- `send_message`: Send chat message
- `disconnect`: Close connection

### REST Endpoints

- `GET /api/agents/status`: System status and metrics
- `POST /api/session/new`: Create new user session
- `GET /api/session/<id>`: Get session information

## Configuration

### System Limits

- **Max Context Length**: 4000 characters per conversation
- **Agent Timeout**: 30 seconds per request
- **Concurrent Users**: 100 simultaneous sessions
- **Session Timeout**: 3600 seconds (1 hour)

### Performance Optimization

- **Connection Pooling**: Efficient database connections
- **Caching**: Intelligent session data caching
- **Rate Limiting**: API call optimization
- **Background Tasks**: Automated cleanup processes

## Development

### Code Structure

```
Multi-Agent-System/
├── agents/                 # Agent implementations
│   ├── base_agent.py      # Base agent class
│   ├── conversational_agent.py
│   ├── memory_agent.py
│   └── matching_agent.py
├── tests/                 # Test suite
├── static/               # Frontend assets
├── templates/            # HTML templates
├── orchestrator.py       # Central coordination
├── app.py               # Flask application
└── config.py            # Configuration
```

### Adding New Agents

1. Create new agent class inheriting from `BaseAgent`
2. Implement required methods: `process()`, `get_status()`
3. Register agent in orchestrator
4. Add comprehensive tests
5. Update documentation

### Contributing

1. Follow existing code patterns and style
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## Troubleshooting

### Common Issues

**API Key Errors:**
- Verify API keys are correctly set in `.env`
- Check API key permissions and quotas
- Ensure keys are not expired

**Connection Issues:**
- Verify all dependencies are installed
- Check port 5000 is available
- Review firewall settings

**Performance Issues:**
- Monitor system resources
- Check database connection limits
- Review API rate limits

### Debug Mode

Enable debug logging by setting:
```env
FLASK_DEBUG=True
```

## Security Considerations

- API keys are stored in environment variables
- Session data is isolated per user
- Input validation on all user data
- Rate limiting prevents abuse
- Secure secret key generation

## Performance Metrics

The system tracks comprehensive metrics:

- **Request Volume**: Total requests processed
- **Response Times**: Average and peak response times
- **Success Rates**: API call success percentages
- **Active Sessions**: Concurrent user count
- **Agent Status**: Real-time agent health monitoring

## Future Enhancements

- **Database Scaling**: PostgreSQL/MongoDB support
- **Advanced Analytics**: User behavior insights
- **Custom Agents**: Plugin architecture
- **API Versioning**: Backward compatibility
- **Monitoring**: Advanced observability tools