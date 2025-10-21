/**
 * Multi-Agent System Frontend Application
 */

class MultiAgentApp {
    constructor() {
        this.socket = null;
        this.userId = null;
        this.sessionId = null;
        this.isConnected = false;
        this.messageHistory = [];
        this.statusUpdateInterval = null;
        
        this.initializeApp();
    }
    
    initializeApp() {
        this.setupEventListeners();
        this.initializeSocket();
        this.createNewSession();
        this.loadSystemStatus();
        this.startStatusUpdates();
    }
    
    setupEventListeners() {
        // Chat input
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        messageInput.addEventListener('input', (e) => {
            this.autoResizeTextarea(e.target);
        });
        
        sendBtn.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Suggestion buttons
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const message = e.target.getAttribute('data-message');
                messageInput.value = message;
                this.sendMessage();
            });
        });
        
        // Control buttons
        document.getElementById('newSessionBtn').addEventListener('click', () => {
            this.createNewSession();
        });
        
        document.getElementById('clearChatBtn').addEventListener('click', () => {
            this.clearChat();
        });
        
        document.getElementById('exportChatBtn').addEventListener('click', () => {
            this.exportChat();
        });
        
        document.getElementById('systemStatusBtn').addEventListener('click', () => {
            this.showSystemStatus();
        });
        
        document.getElementById('refreshAgentsBtn').addEventListener('click', () => {
            this.loadSystemStatus();
        });
        
        // Modal controls
        document.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal();
        });
        
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus();
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus();
        });
        
        this.socket.on('connected', (data) => {
            this.isConnected = true;
        });
        
        this.socket.on('chat_response', (response) => {
            this.handleChatResponse(response);
        });
        
        this.socket.on('system_status', (status) => {
            this.updateSystemStatus(status);
        });
        
        this.socket.on('agent_status', (status) => {
            this.updateAgentStatus(status);
        });
        
        this.socket.on('error', (error) => {
            this.showError(error.message);
        });
    }
    
    async createNewSession() {
        try {
            const response = await fetch('/api/session/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.userId = data.user_id;
                this.sessionId = data.session_id;
                
                this.updateSessionInfo();
                this.joinSession();
                this.clearChat();
                this.updateConversationContext();
            } else {
                throw new Error('Failed to create session');
            }
        } catch (error) {
            this.showError('Failed to create new session');
        }
    }
    
    joinSession() {
        if (this.socket && this.sessionId) {
            this.socket.emit('join_session', {
                session_id: this.sessionId,
                user_id: this.userId
            });
        }
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        if (!this.isConnected) {
            this.showError('Not connected to server');
            return;
        }
        
        // Add user message to chat
        this.addMessageToChat('user', message);
        messageInput.value = '';
        this.autoResizeTextarea(messageInput);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Send message via socket
        this.socket.emit('chat_message', {
            message: message,
            user_id: this.userId,
            session_id: this.sessionId
        });
        
        // Store in history
        this.messageHistory.push({
            type: 'user',
            message: message,
            timestamp: new Date().toISOString()
        });
    }
    
    handleChatResponse(response) {
        this.hideTypingIndicator();
        
        // Clean up response text (remove trailing line breaks)
        const cleanResponse = response.response ? response.response.trim() : '';
        
        // Add assistant response to chat
        this.addMessageToChat('assistant', cleanResponse, response);
        
        // Update context panel
        this.updateContextPanel(response.context);
        
        // Store in history
        this.messageHistory.push({
            type: 'assistant',
            message: cleanResponse,
            metadata: response.metadata,
            context: response.context,
            timestamp: new Date().toISOString()
        });
        
        // Show suggestions if available
        if (response.suggestions && response.suggestions.length > 0) {
            this.showSuggestions(response.suggestions);
        }
    }
    
    addMessageToChat(type, message, metadata = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        
        messageDiv.appendChild(contentDiv);
        
        // Add metadata if available
        if (metadata) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            
            const timestamp = new Date().toLocaleTimeString();
            const responseTime = metadata.metadata?.response_time || metadata.response_time;
            const responseTimeMs = responseTime ? (responseTime * 1000).toFixed(0) + 'ms' : 'N/A';
            
            metaDiv.innerHTML = `
                <span>${timestamp}</span>
                <span>Response time: ${responseTimeMs}</span>
            `;
            
            messageDiv.appendChild(metaDiv);
            
            // Add suggestions if available
            if (metadata.suggestions && metadata.suggestions.length > 0) {
                const suggestionsDiv = document.createElement('div');
                suggestionsDiv.className = 'message-suggestions';
                
                metadata.suggestions.forEach(suggestion => {
                    const chip = document.createElement('span');
                    chip.className = 'suggestion-chip';
                    chip.textContent = suggestion;
                    chip.addEventListener('click', () => {
                        document.getElementById('messageInput').value = suggestion;
                        this.sendMessage();
                    });
                    suggestionsDiv.appendChild(chip);
                });
                
                messageDiv.appendChild(suggestionsDiv);
            }
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant-message typing-indicator';
        typingDiv.id = 'typingIndicator';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<div class="loading"></div> Processing...';
        
        typingDiv.appendChild(contentDiv);
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    showSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('inputSuggestions');
        suggestionsContainer.innerHTML = '';
        
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            btn.setAttribute('data-message', suggestion);
            btn.addEventListener('click', (e) => {
                const message = e.target.getAttribute('data-message');
                document.getElementById('messageInput').value = message;
                this.sendMessage();
            });
            suggestionsContainer.appendChild(btn);
        });
    }
    
    updateSessionInfo() {
        document.getElementById('sessionId').textContent = `Session: ${this.sessionId}`;
        document.getElementById('userId').textContent = `User: ${this.userId}`;
    }
    
    updateConnectionStatus() {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            statusIndicator.textContent = this.isConnected ? 'Connected' : 'Disconnected';
            statusIndicator.className = `connection-status ${this.isConnected ? 'connected' : 'disconnected'}`;
        }
    }
    
    updateContextPanel(context) {
        if (context) {
            // Update sentiment with color coding
            const sentimentEl = document.getElementById('currentSentiment');
            if (sentimentEl) {
                sentimentEl.textContent = context.sentiment || 'neutral';
                sentimentEl.className = `context-value sentiment-${context.sentiment || 'neutral'}`;
            }
            
            // Update intent
            const intentEl = document.getElementById('currentIntent');
            if (intentEl) {
                intentEl.textContent = context.intent || 'general';
            }
            
            // Update confidence
            const confidenceEl = document.getElementById('currentConfidence');
            if (confidenceEl) {
                confidenceEl.textContent = (context.confidence || 0.5).toFixed(2);
            }
        }
        
        // Update conversation context
        this.updateConversationContext();
    }
    
    updateConversationContext() {
        // Add conversation length to context
        const conversationLength = this.messageHistory.length;
        const userMessages = this.messageHistory.filter(msg => msg.type === 'user').length;
        const assistantMessages = this.messageHistory.filter(msg => msg.type === 'assistant').length;
        
        // Update or create conversation stats
        let conversationStats = document.getElementById('conversationStats');
        if (!conversationStats) {
            // Add conversation stats to context panel
            const contextPanel = document.getElementById('contextPanel');
            if (contextPanel) {
                const statsHTML = `
                    <div class="context-item">
                        <span class="context-label">Conversation Length</span>
                        <span class="context-value" id="conversationLength">${conversationLength}</span>
                    </div>
                    <div class="context-item">
                        <span class="context-label">User Messages</span>
                        <span class="context-value" id="userMessages">${userMessages}</span>
                    </div>
                    <div class="context-item">
                        <span class="context-label">Assistant Messages</span>
                        <span class="context-value" id="assistantMessages">${assistantMessages}</span>
                    </div>
                `;
                contextPanel.insertAdjacentHTML('beforeend', statsHTML);
            }
        } else {
            // Update existing stats
            const lengthEl = document.getElementById('conversationLength');
            const userEl = document.getElementById('userMessages');
            const assistantEl = document.getElementById('assistantMessages');
            
            if (lengthEl) lengthEl.textContent = conversationLength;
            if (userEl) userEl.textContent = userMessages;
            if (assistantEl) assistantEl.textContent = assistantMessages;
        }
    }
    
    startStatusUpdates() {
        // Update status every 5 seconds
        this.statusUpdateInterval = setInterval(() => {
            this.loadSystemStatus();
        }, 5000);
    }
    
    stopStatusUpdates() {
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
            this.statusUpdateInterval = null;
        }
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/agents/status');
            if (response.ok) {
                const status = await response.json();
                this.updateSystemStatus(status);
            }
        } catch (error) {
            // System status loading failed silently
        }
    }
    
    updateSystemStatus(status) {
        if (status.system_metrics) {
            document.getElementById('totalRequests').textContent = status.system_metrics.total_requests || 0;
            document.getElementById('activeSessions').textContent = status.system_metrics.active_sessions || 0;
            document.getElementById('avgResponseTime').textContent = 
                status.system_metrics.average_response_time ? 
                (status.system_metrics.average_response_time * 1000).toFixed(0) + 'ms' : '0ms';
            
            const successRate = status.system_metrics.total_requests > 0 ? 
                ((status.system_metrics.successful_requests / status.system_metrics.total_requests) * 100).toFixed(1) + '%' : '100%';
            document.getElementById('successRate').textContent = successRate;
        }
        
        if (status.agent_statuses) {
            this.updateAgentStatus(status.agent_statuses);
        }
    }
    
    updateAgentStatus(agentStatuses) {
        const agentStatusContainer = document.getElementById('agentStatus');
        const agentItems = agentStatusContainer.querySelectorAll('.agent-item');
        
        const agentNames = ['conversational', 'memory', 'matching'];
        
        agentItems.forEach((item, index) => {
            const agentName = agentNames[index];
            const statusElement = item.querySelector('.agent-status');
            const metricsElement = item.querySelector('.agent-metrics small');
            
            if (agentStatuses[agentName]) {
                const status = agentStatuses[agentName];
                statusElement.textContent = status.status || 'idle';
                statusElement.className = `agent-status status-${status.status || 'idle'}`;
                
                if (status.metrics) {
                    metricsElement.textContent = `Requests: ${status.metrics.requests_processed || 0}`;
                }
            }
        });
    }
    
    async showSystemStatus() {
        const modal = document.getElementById('systemStatusModal');
        const content = document.getElementById('systemStatusContent');
        
        // Show loading state
        content.innerHTML = `
            <div class="system-status">
                <h4>System Overview</h4>
                <div class="loading">Loading system status...</div>
            </div>
        `;
        
        modal.style.display = 'block';
        
        try {
            // Fetch fresh data from API
            const response = await fetch('/api/agents/status');
            const status = await response.json();
            
            if (status.system_metrics) {
                const metrics = status.system_metrics;
                const totalRequests = metrics.total_requests || 0;
                const activeSessions = metrics.active_sessions || 0;
                const avgResponseTime = metrics.average_response_time ? 
                    (metrics.average_response_time * 1000).toFixed(0) + 'ms' : '0ms';
                const successRate = totalRequests > 0 ? 
                    ((metrics.successful_requests / totalRequests) * 100).toFixed(1) + '%' : '100%';
                
                content.innerHTML = `
                    <div class="system-status">
                        <h4>System Overview</h4>
                        <div class="status-grid">
                            <div class="status-item">
                                <span class="status-label">Total Requests</span>
                                <span class="status-value">${totalRequests}</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Active Sessions</span>
                                <span class="status-value">${activeSessions}</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Average Response Time</span>
                                <span class="status-value">${avgResponseTime}</span>
                            </div>
                            <div class="status-item">
                                <span class="status-label">Success Rate</span>
                                <span class="status-value">${successRate}</span>
                            </div>
                        </div>
                        <div class="agent-status-section">
                            <h4>Agent Status</h4>
                            <div id="modalAgentStatus">
                                <!-- Agent status will be populated here -->
                            </div>
                        </div>
                    </div>
                `;
                
                // Populate agent status with fresh data
                this.populateModalAgentStatus(status.agent_statuses);
            } else {
                content.innerHTML = `
                    <div class="system-status">
                        <h4>System Overview</h4>
                        <div class="error">Unable to load system status</div>
                    </div>
                `;
            }
        } catch (error) {
            content.innerHTML = `
                <div class="system-status">
                    <h4>System Overview</h4>
                    <div class="error">Error loading system status: ${error.message}</div>
                </div>
            `;
        }
    }
    
    populateModalAgentStatus(agentStatuses = null) {
        const modalAgentStatus = document.getElementById('modalAgentStatus');
        if (!modalAgentStatus) return;
        
        let agentStatusHTML = '';
        
        if (agentStatuses) {
            // Use fresh data from API
            const agentNames = ['conversational', 'memory', 'matching'];
            const displayNames = ['Conversational Agent', 'Memory Agent', 'Matching Agent'];
            
            agentNames.forEach((agentName, index) => {
                const status = agentStatuses[agentName] || {};
                const displayName = displayNames[index];
                const agentStatus = status.status || 'idle';
                const metrics = status.metrics || {};
                const requestsProcessed = metrics.requests_processed || 0;
                
                agentStatusHTML += `
                    <div class="modal-agent-item">
                        <div class="modal-agent-info">
                            <span class="modal-agent-name">${displayName}</span>
                            <span class="modal-agent-status status-${agentStatus.toLowerCase()}">${agentStatus}</span>
                        </div>
                        <div class="modal-agent-metrics">Requests: ${requestsProcessed}</div>
                    </div>
                `;
            });
        } else {
            // Fallback to sidebar data
            const agentItems = document.querySelectorAll('.agent-item');
            
            agentItems.forEach(item => {
                const agentName = item.querySelector('.agent-name')?.textContent || 'Unknown Agent';
                const agentStatus = item.querySelector('.agent-status')?.textContent || 'Unknown';
                const agentMetrics = item.querySelector('.agent-metrics')?.textContent || 'No metrics';
                
                agentStatusHTML += `
                    <div class="modal-agent-item">
                        <div class="modal-agent-info">
                            <span class="modal-agent-name">${agentName}</span>
                            <span class="modal-agent-status status-${agentStatus.toLowerCase()}">${agentStatus}</span>
                        </div>
                        <div class="modal-agent-metrics">${agentMetrics}</div>
                    </div>
                `;
            });
        }
        
        modalAgentStatus.innerHTML = agentStatusHTML;
    }
    
    closeModal() {
        document.getElementById('systemStatusModal').style.display = 'none';
    }
    
    clearChat() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="message system-message">
                <div class="message-content">
                    <i class="fas fa-info-circle"></i>
                    <span>Welcome to the Multi-Agent System! I am powered by specialized AI agents that work together to provide intelligent responses.</span>
                </div>
            </div>
        `;
        this.messageHistory = [];
        
        // Reset context panel
        this.updateConversationContext();
        
        // Reset sentiment, intent, and confidence
        const sentimentEl = document.getElementById('currentSentiment');
        const intentEl = document.getElementById('currentIntent');
        const confidenceEl = document.getElementById('currentConfidence');
        
        if (sentimentEl) {
            sentimentEl.textContent = 'neutral';
            sentimentEl.className = 'context-value sentiment-neutral';
        }
        if (intentEl) intentEl.textContent = 'general';
        if (confidenceEl) confidenceEl.textContent = '0.50';
    }
    
    exportChat() {
        if (this.messageHistory.length === 0) {
            this.showError('No chat history to export');
            return;
        }
        
        const exportData = {
            session_id: this.sessionId,
            user_id: this.userId,
            export_time: new Date().toISOString(),
            messages: this.messageHistory
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${this.sessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    showError(message) {
        const chatMessages = document.getElementById('chatMessages');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message system-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        
        errorDiv.appendChild(contentDiv);
        chatMessages.appendChild(errorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MultiAgentApp();
});
