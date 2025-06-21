import React, { useState, useEffect } from 'react';
import './AIScout.css';

interface ThreatData {
  ip: string;
  threat_type: string;
  confidence: number;
  source: string;
  first_seen: string;
  risk_score: number;
}

interface AnomalyData {
  ip: string;
  anomaly_score: number;
  confidence: number;
  behavior_type: string;
  detected_at: string;
}

interface DashboardData {
  scouts_active: number;
  threats_detected: number;
  anomalies_detected: number;
  auto_blocks_count: number;
  accuracy: number;
  scout_status: Record<string, any>;
  recent_auto_blocks: any[];
  timestamp: string;
}

const AIScout: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [threats, setThreats] = useState<ThreatData[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyData[]>([]);
  const [selectedIP, setSelectedIP] = useState<string>('');
  const [ipAnalysis, setIpAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    // Load initial data
    loadDashboardData();
    loadThreats();
    loadAnomalies();

    // Set up WebSocket for real-time updates
    const ws = new WebSocket('ws://localhost:8001/ws/ai-updates');
    
    ws.onopen = () => {
      setWsConnected(true);
      console.log('🔗 Connected to AI Scout WebSocket');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setDashboardData(data);
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log('❌ Disconnected from AI Scout WebSocket');
    };

    return () => {
      ws.close();
    };
  }, []);

  const loadDashboardData = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/ai/dashboard');
      const data = await response.json();
      setDashboardData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setLoading(false);
    }
  };

  const loadThreats = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/ai/threats');
      const data = await response.json();
      setThreats(data.threats || []);
    } catch (error) {
      console.error('Error loading threats:', error);
    }
  };

  const loadAnomalies = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/ai/anomalies');
      const data = await response.json();
      setAnomalies(data.anomalies || []);
    } catch (error) {
      console.error('Error loading anomalies:', error);
    }
  };

  const analyzeIP = async () => {
    if (!selectedIP) return;
    
    try {
      const response = await fetch(`http://localhost:8001/api/ai/analyze-ip/${selectedIP}`, {
        method: 'POST'
      });
      const data = await response.json();
      setIpAnalysis(data);
    } catch (error) {
      console.error('Error analyzing IP:', error);
    }
  };

  const getRiskBadgeClass = (riskScore: number) => {
    if (riskScore >= 0.8) return 'badge bg-danger';
    if (riskScore >= 0.5) return 'badge bg-warning';
    return 'badge bg-success';
  };

  const getRiskLevel = (riskScore: number) => {
    if (riskScore >= 0.8) return 'HIGH';
    if (riskScore >= 0.5) return 'MEDIUM';
    return 'LOW';
  };

  if (loading) {
    return (
      <div className="ai-scout-container">
        <div className="d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
          <div className="text-center">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">Loading AI Scout...</span>
            </div>
            <h5>🤖 Initializing SecureScout AI Engine...</h5>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-scout-container">
      {/* Header */}
      <div className="row mb-4">
        <div className="col-12">
          <div className="ai-header">
            <h1 className="ai-title">
              🤖 SecureScout AI Dashboard
              <span className={`connection-status ${wsConnected ? 'connected' : 'disconnected'}`}>
                {wsConnected ? '🟢 Live' : '🔴 Offline'}
              </span>
            </h1>
            <p className="ai-subtitle">
              Inspired by <a href="https://blog.yutori.com/p/scouts" target="_blank" rel="noopener noreferrer">Yutori's Scouts</a> - 
              Always-on AI agents monitoring your network security
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="row mb-4">
        <div className="col-md-3">
          <div className="stat-card threats">
            <div className="stat-icon">🔍</div>
            <div className="stat-content">
              <h3>{dashboardData?.scouts_active || 0}/4</h3>
              <p>Active Scouts</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="stat-card blocks">
            <div className="stat-icon">⚡</div>
            <div className="stat-content">
              <h3>{dashboardData?.threats_detected || 0}</h3>
              <p>Threats Detected</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="stat-card accuracy">
            <div className="stat-icon">🎯</div>
            <div className="stat-content">
              <h3>{dashboardData?.accuracy || 0}%</h3>
              <p>Accuracy</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="stat-card auto-blocks">
            <div className="stat-icon">🚫</div>
            <div className="stat-content">
              <h3>{dashboardData?.auto_blocks_count || 0}</h3>
              <p>Auto-Blocked</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Analysis Section */}
      <div className="row mb-4">
        <div className="col-md-6">
          <div className="ai-panel">
            <h4>🔍 IP Risk Analysis</h4>
            <div className="ip-analyzer">
              <div className="input-group mb-3">
                <input
                  type="text"
                  className="form-control"
                  placeholder="Enter IP address to analyze..."
                  value={selectedIP}
                  onChange={(e) => setSelectedIP(e.target.value)}
                />
                <button className="btn btn-primary" onClick={analyzeIP}>
                  Analyze
                </button>
              </div>
              
              {ipAnalysis && (
                <div className="analysis-results">
                  <div className="risk-score-display">
                    <span className="risk-label">Risk Score:</span>
                    <span className={getRiskBadgeClass(ipAnalysis.risk_score)}>
                      {(ipAnalysis.risk_score * 100).toFixed(1)}% - {getRiskLevel(ipAnalysis.risk_score)}
                    </span>
                  </div>
                  <div className="analysis-details mt-3">
                    <h6>Analysis Details:</h6>
                    <ul className="list-unstyled">
                      <li>Request Frequency: {ipAnalysis.analysis.request_frequency}</li>
                      <li>Failed Logins: {ipAnalysis.analysis.failed_login_attempts}</li>
                      <li>Port Scan Activity: {ipAnalysis.analysis.port_scan_activity}</li>
                      <li>Geo Risk Score: {(ipAnalysis.analysis.geo_risk_score * 100).toFixed(1)}%</li>
                      <li>Reputation Score: {(ipAnalysis.analysis.reputation_score * 100).toFixed(1)}%</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-md-6">
          <div className="ai-panel">
            <h4>📊 Scout Status</h4>
            <div className="scout-status">
              <div className="scout-item">
                <span className="scout-name">🛡️ Threat Intelligence</span>
                <span className="badge bg-success">Active</span>
              </div>
              <div className="scout-item">
                <span className="scout-name">🔍 Behavior Analysis</span>
                <span className="badge bg-success">Active</span>
              </div>
              <div className="scout-item">
                <span className="scout-name">🌍 Geolocation Monitor</span>
                <span className="badge bg-success">Active</span>
              </div>
              <div className="scout-item">
                <span className="scout-name">📈 Risk Assessment</span>
                <span className="badge bg-success">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Threats and Anomalies */}
      <div className="row">
        <div className="col-md-6">
          <div className="ai-panel">
            <h4>🚨 Active Threats</h4>
            <div className="threat-list">
              {threats.length === 0 ? (
                <div className="text-center text-muted py-4">
                  <i className="fas fa-shield-alt fa-2x mb-2"></i>
                  <p>No active threats detected</p>
                </div>
              ) : (
                threats.slice(0, 5).map((threat, index) => (
                  <div key={index} className="threat-item">
                    <div className="threat-info">
                      <strong>{threat.ip}</strong>
                      <small className="text-muted d-block">{threat.threat_type}</small>
                    </div>
                    <div className="threat-score">
                      <span className={getRiskBadgeClass(threat.confidence)}>
                        {(threat.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="col-md-6">
          <div className="ai-panel">
            <h4>⚠️ Behavioral Anomalies</h4>
            <div className="anomaly-list">
              {anomalies.length === 0 ? (
                <div className="text-center text-muted py-4">
                  <i className="fas fa-chart-line fa-2x mb-2"></i>
                  <p>No anomalies detected</p>
                </div>
              ) : (
                anomalies.slice(0, 5).map((anomaly, index) => (
                  <div key={index} className="anomaly-item">
                    <div className="anomaly-info">
                      <strong>{anomaly.ip}</strong>
                      <small className="text-muted d-block">{anomaly.behavior_type}</small>
                    </div>
                    <div className="anomaly-score">
                      <span className={getRiskBadgeClass(anomaly.confidence)}>
                        {(anomaly.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Auto-Blocks */}
      {dashboardData?.recent_auto_blocks && dashboardData.recent_auto_blocks.length > 0 && (
        <div className="row mt-4">
          <div className="col-12">
            <div className="ai-panel">
              <h4>🤖 Recent Auto-Blocks</h4>
              <div className="table-responsive">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th>IP Address</th>
                      <th>Reason</th>
                      <th>Risk Score</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData.recent_auto_blocks.slice(0, 10).map((block, index) => (
                      <tr key={index}>
                        <td><code>{block.ip}</code></td>
                        <td>{block.reason}</td>
                        <td>
                          <span className={getRiskBadgeClass(block.risk_score)}>
                            {(block.risk_score * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td>
                          <small>{new Date(block.timestamp).toLocaleString()}</small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="row mt-4">
        <div className="col-12">
          <div className="ai-footer">
            <p className="text-muted text-center">
              🤖 SecureScout AI Engine - Continuously monitoring and protecting your network
              <br />
              <small>
                Last updated: {dashboardData?.timestamp ? new Date(dashboardData.timestamp).toLocaleString() : 'Unknown'}
              </small>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIScout; 