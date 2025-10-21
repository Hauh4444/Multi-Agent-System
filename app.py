"""
Flask Web Application for Multi-Agent System
"""

import asyncio
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import threading
from orchestrator import AIOrchestrator
from config import Config

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

orchestrator = AIOrchestrator()
active_connections = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    try:
        system_status = orchestrator.get_system_status()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": system_status
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
        
        message = data['message']
        user_id = data.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response = loop.run_until_complete(
                orchestrator.handle_request(message, user_id, session_id)
            )
            return jsonify(response)
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": "I apologize, but I encountered an error processing your request."
        }), 500

@app.route('/api/session/new', methods=['POST'])
def create_session():
    """Create a new user session."""
    try:
        user_id = request.json.get('user_id', f"user_{uuid.uuid4().hex[:8]}")
        session_id = str(uuid.uuid4())
        
        session['user_id'] = user_id
        session['session_id'] = session_id
        
        orchestrator.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        return jsonify({
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/<session_id>')
def get_session(session_id):
    """Get session information."""
    try:
        session_info = orchestrator.get_session_info(session_id)
        return jsonify(session_info)
        
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/status')
def get_agents_status():
    """Get status of all agents."""
    try:
        system_status = orchestrator.get_system_status()
        return jsonify(system_status)
        
    except Exception as e:
        logger.error(f"Agent status retrieval failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/<agent_name>/status')
def get_agent_status(agent_name):
    """Get status of a specific agent."""
    try:
        agent_status = orchestrator.get_agent_status(agent_name)
        return jsonify(agent_status)
        
    except Exception as e:
        logger.error(f"Agent status retrieval failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics')
def get_metrics():
    """Get system metrics."""
    try:
        system_status = orchestrator.get_system_status()
        return jsonify({
            "metrics": system_status.get("system_metrics", {}),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        return jsonify({"error": str(e)}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to Multi-Agent System'})

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_connections:
        del active_connections[request.sid]

@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a session."""
    try:
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if session_id:
            join_room(session_id)
            active_connections[request.sid] = {
                'session_id': session_id,
                'user_id': user_id,
                'connected_at': datetime.now().isoformat()
            }
            emit('session_joined', {'session_id': session_id})
        else:
            emit('error', {'message': 'Session ID is required'})
            
    except Exception as e:
        logger.error(f"Join session failed: {e}")
        emit('error', {'message': str(e)})

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle client leaving a session."""
    try:
        session_id = data.get('session_id')
        if session_id:
            leave_room(session_id)
            if request.sid in active_connections:
                del active_connections[request.sid]
            emit('session_left', {'session_id': session_id})
            
    except Exception as e:
        logger.error(f"Leave session failed: {e}")
        emit('error', {'message': str(e)})

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle real-time chat messages."""
    try:
        message = data.get('message')
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        if not message:
            emit('error', {'message': 'Message is required'})
            return
        
        # Process the message through the orchestrator
        def process_message():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                response = loop.run_until_complete(
                    orchestrator.handle_request(message, user_id, session_id)
                )
                
                # Emit response to the session room using socketio context
                with app.app_context():
                    socketio.emit('chat_response', response, room=session_id)
                
            except Exception as e:
                logger.error(f"Message processing failed: {e}")
                with app.app_context():
                    socketio.emit('error', {'message': str(e)}, room=session_id)
            finally:
                loop.close()
        
        # Process message in a separate thread to avoid blocking
        thread = threading.Thread(target=process_message)
        thread.start()
        
    except Exception as e:
        logger.error(f"Chat message handling failed: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_system_status')
def handle_get_system_status():
    """Handle system status requests."""
    try:
        system_status = orchestrator.get_system_status()
        emit('system_status', system_status)
        
    except Exception as e:
        logger.error(f"System status request failed: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_agent_status')
def handle_get_agent_status(data):
    """Handle agent status requests."""
    try:
        agent_name = data.get('agent_name')
        if agent_name:
            agent_status = orchestrator.get_agent_status(agent_name)
            emit('agent_status', {agent_name: agent_status})
        else:
            emit('error', {'message': 'Agent name is required'})
            
    except Exception as e:
        logger.error(f"Agent status request failed: {e}")
        emit('error', {'message': str(e)})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    socketio.run(app, debug=Config.FLASK_DEBUG, host='0.0.0.0', port=5000)
