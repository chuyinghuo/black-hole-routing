import React, { useState, useEffect, useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, BarElement, ArcElement } from 'chart.js';
import { apiService } from '../../services/api';
import { DashboardData } from '../../types';
import './Dashboard.css';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, BarElement, ArcElement);

// Declare Chart constructor for vanilla Chart.js usage
declare const Chart: any;

// Add global Chart access check
const getChart = () => {
  return (window as any).Chart || Chart;
};

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [originalStats, setOriginalStats] = useState<{ total_blocked: number; total_safelist: number }>({ total_blocked: 0, total_safelist: 0 });
  const [loading, setLoading] = useState(true);
  const [currentStatType, setCurrentStatType] = useState<string>('');
  const [quickFilter, setQuickFilter] = useState<string>('');
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');
  const [filterResult, setFilterResult] = useState<string>('');

  // Chart refs
  const creatorChartRef = useRef<HTMLCanvasElement>(null);
  const timelineChartRef = useRef<HTMLCanvasElement>(null);
  const ipTypeChartRef = useRef<HTMLCanvasElement>(null);
  
  // Chart instances
  const creatorChartInstance = useRef<any>(null);
  const timelineChartInstance = useRef<any>(null);
  const ipTypeChartInstance = useRef<any>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await apiService.getDashboardData();
      setDashboardData(data);
      setOriginalStats({
        total_blocked: data.stats.total_blocked,
        total_safelist: data.stats.total_safelist
      });
      
      // Create charts after data is loaded
      setTimeout(() => createCharts(data), 100);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createCharts = (data: DashboardData) => {
    // Destroy existing charts
    if (creatorChartInstance.current) creatorChartInstance.current.destroy();
    if (timelineChartInstance.current) timelineChartInstance.current.destroy();
    if (ipTypeChartInstance.current) ipTypeChartInstance.current.destroy();

    // Creator Chart
    if (creatorChartRef.current) {
      const ChartConstructor = getChart();
      creatorChartInstance.current = new ChartConstructor(creatorChartRef.current, {
        type: 'bar',
        data: {
          labels: Object.keys(data.blocks_by_creator),
          datasets: [{
            label: 'Blocks Created',
            data: Object.values(data.blocks_by_creator),
            backgroundColor: '#012169'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    // Timeline Chart
    if (timelineChartRef.current) {
      const timelineDates = Object.keys(data.timeline_data).sort();
      const ChartConstructor = getChart();
      timelineChartInstance.current = new ChartConstructor(timelineChartRef.current, {
        type: 'line',
        data: {
          labels: timelineDates,
          datasets: [{
            label: 'Blocks Over Time',
            data: timelineDates.map(date => data.timeline_data[date]),
            borderColor: '#012169',
            fill: false,
            tension: 0.3
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    // IP Type Chart
    if (ipTypeChartRef.current) {
      const ChartConstructor = getChart();
      ipTypeChartInstance.current = new ChartConstructor(ipTypeChartRef.current, {
        type: 'pie',
        data: {
          labels: ['IPv4', 'IPv6'],
          datasets: [{
            data: [data.ip_distribution.ipv4, data.ip_distribution.ipv6],
            backgroundColor: ['#012169', '#b5b5b5']
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }
  };

  const getQuickFilterDates = (filter: string): { from: string; to: string } => {
    const now = new Date();
    const today = now.toISOString().split('T')[0];
    
    switch(filter) {
      case 'today':
        return { from: today, to: today };
      case 'last7':
        const last7 = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return { from: last7.toISOString().split('T')[0], to: today };
      case 'last30':
        const last30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return { from: last30.toISOString().split('T')[0], to: today };
      case 'month':
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        return { from: firstDay.toISOString().split('T')[0], to: today };
      default:
        return { from: '', to: '' };
    }
  };

  const handleStatCardClick = (type: string) => {
    setCurrentStatType(type);
    resetForm();
    
    // Update modal title
    const modalTitle = document.getElementById('filterStatsModalLabel');
    if (modalTitle) {
      modalTitle.textContent = type === 'blocklist' ? 'Filter Total Blocked IPs' : 'Filter Total Safelisted IPs';
    }
  };

  const resetForm = () => {
    setQuickFilter('');
    setFromDate('');
    setToDate('');
    setFilterResult('');
  };

  const handleQuickFilterChange = (value: string) => {
    setQuickFilter(value);
    if (value) {
      const dates = getQuickFilterDates(value);
      setFromDate(dates.from);
      setToDate(dates.to);
    }
  };

  const handleFilterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!fromDate || !toDate) {
      alert('Please select both from and to dates');
      return;
    }

    setFilterResult('Loading...');

    try {
      const result = await apiService.filterStats(currentStatType, { from: fromDate, to: toDate });
      
      // Update the displayed value
      const elementId = currentStatType === 'blocklist' ? 'totalBlocked' : 'totalSafe';
      const element = document.getElementById(elementId);
      if (element) {
        element.textContent = result.count.toString();
      }
      
      // Close modal using Bootstrap JS
      const modalElement = document.getElementById('filterStatsModal');
      if (modalElement) {
        const modalInstance = (window as any).bootstrap?.Modal?.getInstance(modalElement);
        if (modalInstance) {
          modalInstance.hide();
        }
      }
    } catch (error) {
      console.error('Filter error:', error);
      setFilterResult('An error occurred.');
    }
  };

  const handleClearFilter = () => {
    // Reset to original values
    const totalBlockedEl = document.getElementById('totalBlocked');
    const totalSafeEl = document.getElementById('totalSafe');
    
    if (totalBlockedEl) totalBlockedEl.textContent = originalStats.total_blocked.toString();
    if (totalSafeEl) totalSafeEl.textContent = originalStats.total_safelist.toString();
    
    resetForm();
    
    // Close modal
    const modalElement = document.getElementById('filterStatsModal');
    if (modalElement) {
      const modalInstance = (window as any).bootstrap?.Modal?.getInstance(modalElement);
      if (modalInstance) {
        modalInstance.hide();
      }
    }
  };

  if (loading || !dashboardData) {
    return (
      <div className="container-fluid px-4 py-5">
        <h1 className="mb-4">Black Hole Router</h1>
        <h2 className="mb-4">Welcome Paulina!</h2>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <>
      <div className="container-fluid px-4 py-5">
        <h1 className="mb-4">Black Hole Router</h1>
        <h2 className="mb-4">Welcome Paulina!</h2>

        {/* Stats Row */}
        <div className="row g-4 mb-4">
          <div className="col-xl-3 col-md-6">
            <div 
              className="card stat-card primary shadow-sm" 
              data-bs-toggle="modal" 
              data-bs-target="#filterStatsModal" 
              data-type="blocklist"
              onClick={() => handleStatCardClick('blocklist')}
              style={{ cursor: 'pointer' }}
            >
              <div className="card-body">
                <h5 className="card-title text-muted">Total Blocked IPs</h5>
                <h2 className="card-text" id="totalBlocked">{dashboardData.stats.total_blocked}</h2>
                <p className="mb-0 text-muted">Active blocks</p>
              </div>
            </div>
          </div>
          <div className="col-xl-3 col-md-6">
            <div 
              className="card stat-card success shadow-sm" 
              data-bs-toggle="modal" 
              data-bs-target="#filterStatsModal" 
              data-type="safelist"
              onClick={() => handleStatCardClick('safelist')}
              style={{ cursor: 'pointer' }}
            >
              <div className="card-body">
                <h5 className="card-title text-muted">Total Safelisted IPs</h5>
                <h2 className="card-text" id="totalSafe">{dashboardData.stats.total_safelist}</h2>
                <p className="mb-0 text-muted">Active safelist entries</p>
              </div>
            </div>
          </div>
          <div className="col-xl-3 col-md-6">
            <div className="card stat-card warning shadow-sm">
              <div className="card-body">
                <h5 className="card-title text-muted">Peak Activity Hour</h5>
                <h2 className="card-text" id="peakHour">{dashboardData.stats.peak_hour}</h2>
                <p className="mb-0 text-muted">This week</p>
              </div>
            </div>
          </div>
          <div className="col-xl-3 col-md-6">
            <div className="card stat-card danger shadow-sm">
              <div className="card-body">
                <h5 className="card-title text-muted">Peak Activity Day</h5>
                <h2 className="card-text" id="peakDay">{dashboardData.stats.peak_day}</h2>
                <p className="mb-0 text-muted">This month</p>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="row g-4">
          <div className="col-xl-6">
            <div className="card shadow-sm">
              <div className="card-body">
                <h5 className="card-title">Blocks by Creator</h5>
                <div className="chart-container">
                  <canvas ref={creatorChartRef} id="creatorChart"></canvas>
                </div>
              </div>
            </div>
          </div>
          <div className="col-xl-6">
            <div className="card shadow-sm">
              <div className="card-body">
                <h5 className="card-title">Timeline of Actions</h5>
                <div className="chart-container">
                  <canvas ref={timelineChartRef} id="timelineChart"></canvas>
                </div>
              </div>
            </div>
          </div>
          <div className="col-xl-6">
            <div className="card shadow-sm">
              <div className="card-body">
                <h5 className="card-title">IP Type Distribution</h5>
                <div className="chart-container">
                  <canvas ref={ipTypeChartRef} id="ipTypeChart"></canvas>
                </div>
              </div>
            </div>
          </div>
          <div className="col-xl-6">
            <div className="card shadow-sm">
              <div className="card-body">
                <h5 className="card-title">Recent Activity</h5>
                <div className="table-responsive">
                  <table className="table table-sm">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Action</th>
                        <th>IP</th>
                        <th>User</th>
                      </tr>
                    </thead>
                    <tbody id="recentActivity">
                      {dashboardData.recent_activity.map((entry, index) => (
                        <tr key={index}>
                          <td>{new Date(entry.added_at).toLocaleString()}</td>
                          <td>Block</td>
                          <td>{entry.ip_address}</td>
                          <td>{entry.created_by}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Modal */}
      <div className="modal fade" id="filterStatsModal" tabIndex={-1} aria-labelledby="filterStatsModalLabel" aria-hidden="true">
        <div className="modal-dialog">
          <div className="modal-content">
            <form id="filterStatsForm" onSubmit={handleFilterSubmit}>
              <div className="modal-header">
                <h5 className="modal-title" id="filterStatsModalLabel">Filter by Date</h5>
                <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>

              <div className="modal-body">
                {/* Hidden field to store the stat type */}
                <input type="hidden" id="currentStatType" value={currentStatType} />
                
                {/* Quick Filter */}
                <div className="mb-3">
                  <label htmlFor="quickFilter" className="form-label">Quick Filter</label>
                  <select 
                    className="form-select" 
                    id="quickFilter"
                    value={quickFilter}
                    onChange={(e) => handleQuickFilterChange(e.target.value)}
                  >
                    <option value="">Select...</option>
                    <option value="today">Today</option>
                    <option value="last7">Last 7 Days</option>
                    <option value="last30">Last 30 Days</option>
                    <option value="month">This Month</option>
                  </select>
                </div>

                {/* Custom Date Range */}
                <div className="mb-3">
                  <label className="form-label">Or Select Range</label>
                  <input 
                    type="date" 
                    className="form-control mb-2" 
                    id="fromDate"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                  />
                  <input 
                    type="date" 
                    className="form-control" 
                    id="toDate"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                  />
                </div>

                {/* Result Display */}
                <div id="filterResult" className="mt-3">
                  {filterResult}
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" id="clearFilter" onClick={handleClearFilter}>
                  Clear Filter
                </button>
                <button type="submit" className="btn btn-success">Apply Filter</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
};

export default Dashboard; 