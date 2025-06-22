import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import './GuardianToggle.css';

interface GuardianStatus {
  available: boolean;
  enabled: boolean;
  guardian_initialized: boolean;
}

interface GuardianToggleProps {
  onStatusChange?: (enabled: boolean) => void;
}

const GuardianToggle: React.FC<GuardianToggleProps> = ({ onStatusChange }) => {
  const [status, setStatus] = useState<GuardianStatus>({
    available: false,
    guardian_initialized: false,
    enabled: false
  });
  const [loading, setLoading] = useState(true);
  const [showInfo, setShowInfo] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const statusData = await apiService.getGuardianStatus();
      setStatus(statusData);
    } catch (error) {
      console.error('Failed to load Guardian status:', error);
      setMessage('Failed to load Guardian status');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    if (!status.available) return;

    try {
      setToggling(true);
      const newEnabled = !status.enabled;
      const result = await apiService.toggleGuardian(newEnabled);
      
      setStatus(prev => ({ ...prev, enabled: newEnabled }));
      setMessage(result.message || `Guardian ${newEnabled ? 'enabled' : 'disabled'}`);
      
      if (onStatusChange) {
        onStatusChange(newEnabled);
      }

      // Clear message after 3 seconds
      setTimeout(() => setMessage(''), 3000);
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to toggle Guardian');
      setTimeout(() => setMessage(''), 5000);
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return (
      <div className="guardian-toggle-container">
        <div className="guardian-loading">Loading Guardian...</div>
      </div>
    );
  }

  return (
    <div className="guardian-toggle-container">
      <div className="guardian-header">
        <div className="guardian-status">
          <span className="guardian-label">Guardian Protection</span>
          <div className="toggle-group">
            <div className={`toggle-switch ${!status.available ? 'disabled' : ''}`}>
              <input
                type="checkbox"
                id="guardian-toggle"
                checked={status.enabled}
                onChange={handleToggle}
                disabled={!status.available || toggling}
              />
              <label htmlFor="guardian-toggle" className="toggle-label">
                <span className="toggle-slider"></span>
              </label>
            </div>
            <button
              className="info-circle"
              onClick={() => setShowInfo(!showInfo)}
              title="Learn about Guardian"
            >
              <span className="info-icon">i</span>
            </button>
          </div>
        </div>
        
        <div className="guardian-status-indicators">
          <span className={`status-dot ${status.available ? 'available' : 'unavailable'}`}></span>
          <span className="status-text">
            {!status.available ? 'Unavailable' : status.enabled ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      {message && (
        <div className={`guardian-message ${message.includes('error') || message.includes('Failed') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}

      {showInfo && (
        <div className="guardian-info-panel">
          <div className="info-header">
            <h4>Guardian Protection System</h4>
            <p className="text-muted">
              AI-powered protection against blocking critical infrastructure
            </p>
            <button className="close-info" onClick={() => setShowInfo(false)}>×</button>
          </div>
          
          <div className="info-content">
            <div className="info-grid">
              <div className="info-column">
                <h5>Risk Levels:</h5>
                <ul className="risk-levels-list">
                  <li><strong>CRITICAL:</strong> DNS, localhost</li>
                  <li><strong>HIGH:</strong> Important services</li>
                  <li><strong>MEDIUM:</strong> Moderate risk</li>
                  <li><strong>LOW:</strong> Low risk</li>
                  <li><strong>SAFE:</strong> Safe to block</li>
                </ul>
                
                <h5>Protected Networks:</h5>
                <ul className="compact-list">
                  <li><strong>DNS:</strong> Google, Cloudflare, OpenDNS</li>
                  <li><strong>Private:</strong> 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16</li>
                  <li><strong>Cloud:</strong> AWS, Azure, Cloudflare ranges</li>
                </ul>
              </div>
              
              <div className="info-column">
                <h5>Features:</h5>
                <ul className="compact-list">
                  <li>Real-time analysis</li>
                  <li>Impact assessment</li>
                  <li>Business evaluation</li>
                  <li>Security alternatives</li>
                  <li>Detailed explanations</li>
                </ul>
                
                <h5>Status:</h5>
                <div className="status-grid">
                  <div className="status-item">
                    <strong>Available:</strong> {status.available ? 'Yes' : 'No'}
                  </div>
                  <div className="status-item">
                    <strong>Initialized:</strong> {status.guardian_initialized ? 'Yes' : 'No'}
                  </div>
                  <div className="status-item">
                    <strong>Protection:</strong> {status.enabled ? 'Active' : 'Inactive'}
                  </div>
                </div>
                
                <div className="remaining-networks">
                  <ul className="compact-list">
                    <li><strong>Development:</strong> GitHub, localhost</li>
                    <li><strong>Large subnets:</strong> Networks affecting 1000+ IPs</li>
                  </ul>
                </div>
              </div>
            </div>

            {!status.available && (
              <div className="info-section setup-section">
                <h5>Setup:</h5>
                <div className="setup-code">
                  <code>pip install -r ai-scout/requirements-ai.txt</code>
                </div>
                <p>Install AI dependencies to enable Guardian protection.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GuardianToggle; 