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
  const [showThemeSelector, setShowThemeSelector] = useState(false);
  const [currentTheme, setCurrentTheme] = useState('default');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const themes = {
    default: { name: 'Default Enhanced', bg: 'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)', chatBg: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)', userBubble: 'linear-gradient(135deg, #00d4ff 0%, #0099cc 100%)', aiBubble: '#2a2a2a', primary: '#00d4ff', text: '#ffffff', sidebarBg: 'rgba(15, 32, 39, 0.95)', sidebarText: '#ffffff', inputBg: '#2a2a2a', inputBorder: '#00d4ff' },
    executive: { name: 'Executive Dark', bg: 'linear-gradient(180deg, #1a1a1a 0%, #121212 100%)', chatBg: '#1a1a1a', userBubble: '#1e2a38', aiBubble: '#242424', primary: '#009b9b', text: '#e0e0e0', sidebarBg: 'rgba(26, 26, 26, 0.95)', sidebarText: '#e0e0e0', inputBg: '#242424', inputBorder: '#2a2a2a' },
    professional: { name: 'Professional Light', bg: '#f5f5f5', chatBg: '#f5f5f5', userBubble: '#d0e2f2', aiBubble: '#eaeaea', primary: '#3a7ca5', text: '#333333', sidebarBg: 'rgba(51, 51, 51, 0.95)', sidebarText: '#ffffff', inputBg: '#ffffff', inputBorder: '#d0e2f2' },
    calm: { name: 'Calm Neutral', bg: '#f8f8f6', chatBg: '#f8f8f6', userBubble: '#deddda', aiBubble: '#ececea', primary: '#6b8e78', text: '#2f2f2f', sidebarBg: 'rgba(47, 47, 47, 0.95)', sidebarText: '#ffffff', inputBg: '#ffffff', inputBorder: '#deddda' },
    midnight: { name: 'Midnight Steel', bg: 'linear-gradient(180deg, #1e1e2f 0%, #151521 100%)', chatBg: 'linear-gradient(180deg, #1e1e2f 0%, #151521 100%)', userBubble: '#2e3a4f', aiBubble: '#222233', primary: '#5d85aa', text: '#dddddd', sidebarBg: 'rgba(30, 30, 47, 0.95)', sidebarText: '#dddddd', inputBg: '#222233', inputBorder: '#2e3a4f' }
  };

  const applyTheme = (themeKey) => {
    const theme = themes[themeKey];
    const root = document.documentElement;
    root.style.setProperty('--bg-color', theme.bg);
    root.style.setProperty('--primary-color', theme.primary);
    root.style.setProperty('--accent1-color', theme.accent1);
    root.style.setProperty('--accent2-color', theme.accent2);
    root.style.setProperty('--text-color', theme.text);
    root.style.setProperty('--sidebar-bg', theme.sidebarBg);
    root.style.setProperty('--sidebar-text', theme.sidebarText);
    setCurrentTheme(themeKey);
    setShowThemeSelector(false);
  };

  useEffect(() => {
    applyTheme('default');
  }, []);



  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.theme-button') && !event.target.closest('.theme-selector-floating')) {
        setShowThemeSelector(false);
      }

    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

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
      
      <div className="theme-button" onClick={() => setShowThemeSelector(!showThemeSelector)}>
        🎨
      </div>
      
      {showThemeSelector && (
        <div className="theme-selector-floating">
          {Object.entries(themes).map(([key, theme]) => (
            <div 
              key={key}
              className={`theme-option ${currentTheme === key ? 'active' : ''}`}
              onClick={() => applyTheme(key)}
            >
              <div className="theme-preview" style={{backgroundColor: theme.primary}}></div>
              <span>{theme.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;