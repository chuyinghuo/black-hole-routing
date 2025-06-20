import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import Dashboard from './pages/Dashboard/Dashboard';
import Blocklist from './pages/Blocklist/Blocklist';
import Safelist from './pages/Safelist/Safelist';
import Users from './pages/Users/Users';
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <div className="bg-light" style={{ display: 'flex' }}>
      <Router>
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/blocklist" element={<Blocklist />} />
            <Route path="/safelist" element={<Safelist />} />
            <Route path="/users" element={<Users />} />
          </Routes>
        </div>
      </Router>
    </div>
  );
}

export default App;
