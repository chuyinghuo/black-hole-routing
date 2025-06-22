import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import Dashboard from './pages/Dashboard/Dashboard';
import Blocklist from './pages/Blocklist/Blocklist';
import Safelist from './pages/Safelist/Safelist';
import Users from './pages/Users/Users';
import AIScout from './pages/AIScout/AIScout';
import Chatbot from './components/Chatbot/Chatbot';
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  const [chatbotOpen, setChatbotOpen] = React.useState(false);

  const toggleChatbot = () => {
    setChatbotOpen(!chatbotOpen);
  };

  return (
    <div className="bg-light" style={{ display: 'flex' }}>
      <Router>
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/blocklist" element={<Blocklist />} />
            <Route path="/safelist" element={<Safelist />} />
            <Route path="/users" element={<Users />} />
            <Route path="/ai-scout" element={<AIScout />} />
          </Routes>
        </div>
        
        {/* Chatbot Component */}
        <Chatbot isOpen={chatbotOpen} onToggle={toggleChatbot} />
      </Router>
    </div>
  );
}

export default App;
