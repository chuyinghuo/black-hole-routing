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
    enabled: false,
    guardian_initialized: false
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

  const getRiskBadge = (level: string) => {
    const badges = {
      'CRITICAL': '🚫',
      'HIGH': '⚠️',
      'MEDIUM': '🔶',
      'LOW': '🔶',
      'SAFE': '✅'
    };
    return badges[level as keyof typeof badges] || '❓';
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
          <span className="guardian-label">IP Guardian</span>
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
              title="Learn about IP Guardian"
            >
              <span className="info-icon">ℹ️</span>
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
            <h4>🛡️ IP Guardian Protection System</h4>
            <button className="close-info" onClick={() => setShowInfo(false)}>×</button>
          </div>
          
          <div className="info-content">
            <div className="info-section">
              <h5>🎯 What it does:</h5>
              <p>AI-powered agent that prevents you from accidentally blocking critical infrastructure that could cause network outages.</p>
            </div>

            <div className="info-section">
              <h5>🛡️ Protection Levels:</h5>
              <div className="risk-levels">
                <div className="risk-item">
                  <span className="risk-badge">{getRiskBadge('CRITICAL')}</span>
                  <span className="risk-text"><strong>CRITICAL:</strong> Do not block - would cause severe infrastructure damage</span>
                </div>
                <div className="risk-item">
                  <span className="risk-badge">{getRiskBadge('HIGH')}</span>
                  <span className="risk-text"><strong>HIGH:</strong> Manual review required before blocking</span>
                </div>
                <div className="risk-item">
                  <span className="risk-badge">{getRiskBadge('MEDIUM')}</span>
                  <span className="risk-text"><strong>MEDIUM:</strong> Proceed with caution, monitor for impact</span>
                </div>
                <div className="risk-item">
                  <span className="risk-badge">{getRiskBadge('SAFE')}</span>
                  <span className="risk-text"><strong>SAFE:</strong> No significant risks detected</span>
                </div>
              </div>
            </div>

            <div className="info-section">
              <h5>🔒 Protected Networks:</h5>
              <ul>
                <li><strong>DNS Servers:</strong> Google (8.8.8.8), Cloudflare (1.1.1.1), OpenDNS</li>
                <li><strong>Private Networks:</strong> 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16</li>
                <li><strong>Cloud Providers:</strong> AWS, Cloudflare, Azure ranges</li>
                <li><strong>Development:</strong> GitHub, localhost, link-local</li>
                <li><strong>Large Subnets:</strong> Networks affecting 1000+ IPs</li>
              </ul>
            </div>

            <div className="info-section">
              <h5>🤖 AI Features:</h5>
              <ul>
                <li>Real-time threat intelligence analysis</li>
                <li>Geolocation and provider verification</li>
                <li>Network impact assessment</li>
                <li>Historical pattern learning</li>
                <li>Context-aware bulk operation protection</li>
              </ul>
            </div>

            <div className="info-section">
              <h5>📊 Status Information:</h5>
              <div className="status-info">
                <div className="status-row">
                  <span>Available:</span>
                  <span className={status.available ? 'status-yes' : 'status-no'}>
                    {status.available ? '✅ Yes' : '❌ No (Install dependencies)'}
                  </span>
                </div>
                <div className="status-row">
                  <span>Initialized:</span>
                  <span className={status.guardian_initialized ? 'status-yes' : 'status-no'}>
                    {status.guardian_initialized ? '✅ Yes' : '⚠️ No'}
                  </span>
                </div>
                <div className="status-row">
                  <span>Protection:</span>
                  <span className={status.enabled ? 'status-active' : 'status-inactive'}>
                    {status.enabled ? '🛡️ Active' : '💤 Inactive'}
                  </span>
                </div>
              </div>
            </div>

            {!status.available && (
              <div className="info-section">
                <h5>⚙️ Setup Instructions:</h5>
                <div className="setup-code">
                  <code>pip install -r ai-scout/requirements-ai.txt</code>
                </div>
                <p>Install the required AI dependencies to enable Guardian protection.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GuardianToggle; 