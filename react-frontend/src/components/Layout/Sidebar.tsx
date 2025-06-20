import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  useEffect(() => {
    // Add Bootstrap Icons CSS
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    return () => {
      document.head.removeChild(link);
    };
  }, []);

  const handleLogout = () => {
    // Add logout logic here if needed
    console.log('Logout clicked');
  };

  return (
    <div className="sidebar">
      <div>
        <div className="logo">
          <img src="/images/dukeLogo.png" alt="BHR Logo" />
        </div>
        <ul className="nav-links">
          <li className="nav-item">
            <NavLink to="/dashboard">
              <i className="bi bi-house-door-fill"></i> Home
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/blocklist">
              <i className="bi bi-shield-fill-exclamation"></i> Blocklist
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/safelist">
              <i className="bi bi-shield-check"></i> Safelist
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/users">
              <i className="bi bi-people-fill"></i> Users
            </NavLink>
          </li>
        </ul>
      </div>
      <div>
        <button className="logout-btn" onClick={handleLogout}>
          Log Out
        </button>
      </div>
    </div>
  );
};

export default Sidebar; 