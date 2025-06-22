import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface ChatbotProps {
  isOpen: boolean;
  onToggle: () => void;
}

const Chatbot: React.FC<ChatbotProps> = ({ isOpen, onToggle }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hi! I can help you understand why certain IPs might be crucial to block or not block. Try asking me about specific IP addresses!',
      isUser: false,
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Call the Gemini chatbot API
      const response = await fetch('/api/chatbot/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: inputText
        })
      });

      const data = await response.json();

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.answer || 'Sorry, I encountered an error processing your question.',
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Chatbot error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I\'m having trouble connecting right now. Please try again later.',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        text: 'Hi! I can help you understand why certain IPs might be crucial to block or not block. Try asking me about specific IP addresses!',
        isUser: false,
        timestamp: new Date()
      }
    ]);
  };

  if (!isOpen) {
    return (
      <div className="chatbot-toggle" onClick={onToggle}>
        <i className="bi bi-chat-dots"></i>
        <span>Ask AI</span>
      </div>
    );
  }

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <i className="bi bi-robot"></i>
          <span>IP Security Assistant</span>
        </div>
        <div className="chatbot-controls">
          <button 
            className="btn-clear" 
            onClick={clearChat}
            title="Clear chat"
          >
            <i className="bi bi-arrow-clockwise"></i>
          </button>
          <button 
            className="btn-minimize" 
            onClick={onToggle}
            title="Minimize chat"
          >
            <i className="bi bi-dash"></i>
          </button>
        </div>
      </div>

      <div className="chatbot-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.isUser ? 'user-message' : 'bot-message'}`}
          >
            <div className="message-content">
              <div className="message-text">{message.text}</div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message bot-message">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <div className="input-container">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about IP addresses, security risks, or blocking decisions..."
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim() || isLoading}
            className="send-button"
          >
            <i className="bi bi-send"></i>
          </button>
        </div>
        <div className="chatbot-examples">
          <span>Try asking:</span>
          <button 
            className="example-question"
            onClick={() => setInputText('Why is 8.8.8.8 crucial not to block?')}
          >
            "Why is 8.8.8.8 crucial not to block?"
          </button>
          <button 
            className="example-question"
            onClick={() => setInputText('What happens if I block 192.168.1.1?')}
          >
            "What happens if I block 192.168.1.1?"
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot; 