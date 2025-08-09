import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { id: 1, content: "Hello! I'm Simi, your AI assistant. How can I help you today?", isUser: false, agent: 'Simi.ai' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const autoResize = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    autoResize();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const setQuickAction = (action) => {
    setInputValue(action);
    textareaRef.current?.focus();
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      content: inputValue,
      isUser: true
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      console.log('Sending request with session_id:', sessionId);
      const response = await axios.post('http://localhost:8000/process', {
        query: inputValue,
        session_id: sessionId
      });

      console.log('Received response:', response.data);
      // Store session ID from response
      if (response.data.session_id) {
        console.log('Setting new session_id:', response.data.session_id);
        setSessionId(response.data.session_id);
      }

      const botMessage = {
        id: Date.now() + 1,
        content: response.data.response,
        isUser: false,
        agent: response.data.agent || 'Simi.ai'
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        content: `Sorry, I encountered an error: ${error.message}`,
        isUser: false,
        agent: 'System',
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  return (
    <div className="app">
      <div className="background-pattern"></div>
      
      <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <h1>Simi<span className="ai">.ai</span></h1>
          <button className="toggle-btn" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>
        <div className="sidebar-menu">
          <div className="menu-item active">
            <span className="menu-icon">◉</span>
            <span>Chat</span>
          </div>
          <div className="menu-item">
            <span className="menu-icon">✉</span>
            <span>Email</span>
          </div>
          <div className="menu-item">
            <span className="menu-icon">☐</span>
            <span>Tasks</span>
          </div>
          <div className="menu-item">
            <span className="menu-icon">▲</span>
            <span>Analytics</span>
          </div>
        </div>
      </div>

      <main className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="chat-container">
          <div className={`chat-messages ${messages.filter(msg => msg.isUser).length === 0 ? 'centered' : ''}`}>
            {messages.filter(msg => msg.isUser).length === 0 && (
              <div className="welcome-section">
                <h2 className="welcome-title">Welcome to Simi.ai</h2>
                <p className="welcome-subtitle">Your intelligent multi-agent assistant</p>
              </div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.isUser ? 'user-message' : 'bot-message'} ${message.isError ? 'error-message' : ''}`}>
                {!message.isUser && (
                  <div className="agent-label">{message.agent}</div>
                )}
                <div className="message-content">
                  {message.content.split('\n').map((line, index) => (
                    <React.Fragment key={index}>
                      {line}
                      {index < message.content.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message bot-message">
                <div className="agent-label">Simi.ai</div>
                <div className="loading">
                  <div className="loading-spinner"></div>
                  <span>Processing your request...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className={`input-container ${messages.filter(msg => msg.isUser).length === 0 ? 'centered-input' : ''}`}>
            <textarea
              ref={textareaRef}
              className="input-field"
              value={inputValue}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              rows="1"
              disabled={isLoading}
            />
            <button 
              className="send-button" 
              onClick={sendMessage}
              disabled={isLoading || !inputValue.trim()}
            >
              <span className="send-icon">→</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;