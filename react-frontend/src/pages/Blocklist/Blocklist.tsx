import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { BlocklistEntry, BlocklistFormData, FilterOptions } from '../../types';
import GuardianToggle from '../../components/Guardian/GuardianToggle';
import './Blocklist.css';

const Blocklist: React.FC = () => {
  const [entries, setEntries] = useState<BlocklistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string>('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [currentEntry, setCurrentEntry] = useState<BlocklistEntry | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState('added_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [guardianEnabled, setGuardianEnabled] = useState(false);
  const [ipValidation, setIpValidation] = useState<{ ip: string; status: any } | null>(null);
  const [criticalRiskIPs, setCriticalRiskIPs] = useState<Set<string>>(new Set());
  const [showExplanationModal, setShowExplanationModal] = useState(false);
  const [currentExplanation, setCurrentExplanation] = useState<{
    ip: string;
    explanation: string;
    riskLevel: string;
    confidence: number;
    reasons: string[];
    loading: boolean;
  } | null>(null);

  // Guardian warning modal state
  const [showGuardianWarning, setShowGuardianWarning] = useState(false);
  const [guardianWarningData, setGuardianWarningData] = useState<{
    riskLevel: string;
    confidence: number;
    reason: string;
    ipAddress: string;
    onConfirm: () => void;
    onCancel: () => void;
  } | null>(null);

  // Form states
  const [addFormData, setAddFormData] = useState<BlocklistFormData>({
    ip_address: '',
    time_added: new Date().toISOString().slice(0, 16),
    duration: '24',
    comment: '',
    blocks_count: '1',
    created_by: ''
  });

  const [editFormData, setEditFormData] = useState({
    ip_address: '',
    time_unblocked: '',
    comment: ''
  });

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    loadEntries();
  }, [sortColumn, sortOrder, debouncedSearchTerm]);

  // Check critical risk IPs when Guardian status changes
  useEffect(() => {
    if (guardianEnabled && entries.length > 0) {
      checkCriticalRiskIPs(entries);
    } else if (!guardianEnabled) {
      setCriticalRiskIPs(new Set());
    }
  }, [guardianEnabled, entries]);

  // Real-time IP validation when Guardian is enabled
  useEffect(() => {
    if (!guardianEnabled || !addFormData.ip_address.trim()) {
      setIpValidation(null);
      return;
    }

    const validateIP = async () => {
      try {
        const result = await apiService.validateIP(addFormData.ip_address);
        setIpValidation({ ip: addFormData.ip_address, status: result });
      } catch (error) {
        console.error('IP validation failed:', error);
        setIpValidation(null);
      }
    };

    const timer = setTimeout(validateIP, 500);
    return () => clearTimeout(timer);
  }, [addFormData.ip_address, guardianEnabled]);

  const loadEntries = async () => {
    try {
      setLoading(true);
      const filters: FilterOptions = {
        search: debouncedSearchTerm || undefined,
        sort: sortColumn,
        order: sortOrder
      };
      const data = await apiService.getBlocklistEntries(filters);
      setEntries(Array.isArray(data) ? data : []);
      
      // Always check which IPs are critical risk (will be shown only when Guardian is enabled)
      if (Array.isArray(data) && data.length > 0) {
        checkCriticalRiskIPs(data);
      }
    } catch (error) {
      console.error('Error loading blocklist entries:', error);
      setMessage('Error loading blocklist entries');
      setEntries([]); // Ensure entries is always an array
    } finally {
      setLoading(false);
    }
  };

  const checkCriticalRiskIPs = async (entries: BlocklistEntry[]) => {
    const criticalIPs = new Set<string>();
    
    // Force 8.8.8.8 to be critical for testing
    const googleDNS = entries.find(entry => entry.ip_address === '8.8.8.8');
    if (googleDNS) {
      criticalIPs.add('8.8.8.8');
      console.log('🚨 FORCED: Added 8.8.8.8 to critical risk set for testing');
    }
    
    // Check each IP's risk level in parallel
    const riskChecks = entries.map(async (entry) => {
      try {
        const data = await apiService.getAIExplanation(entry.ip_address);
        console.log(`Risk check for ${entry.ip_address}:`, data.risk_level); // Debug log
        
        // Check for critical risk (case insensitive)
        if (data.risk_level && data.risk_level.toLowerCase() === 'critical') {
          criticalIPs.add(entry.ip_address);
          console.log(`Added ${entry.ip_address} to critical risk set`); // Debug log
        }
      } catch (error) {
        // Silently ignore errors for individual IP checks
        console.debug(`Failed to check risk for ${entry.ip_address}:`, error);
      }
    });
    
    // Wait for all checks to complete
    await Promise.all(riskChecks);
    console.log('Critical IPs detected:', Array.from(criticalIPs)); // Debug log
    console.log('Total critical IPs count:', criticalIPs.size); // Debug log
    setCriticalRiskIPs(criticalIPs);
  };

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortOrder('asc');
    }
  };

  const getSortIcon = (column: string) => {
    if (sortColumn !== column) return '';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  const handleSearch = () => {
    loadEntries();
  };

  const handleSearchKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL': return '#f44336';
      case 'HIGH': return '#ff9800';
      case 'MEDIUM': return '#2196f3';
      case 'LOW': return '#2196f3';
      case 'SAFE': return '#4caf50';
      default: return '#757575';
    }
  };

  const getRiskLevelIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL': return 'CRITICAL';
      case 'HIGH': return 'HIGH';
      case 'MEDIUM': return 'MEDIUM';
      case 'LOW': return 'LOW';
      case 'SAFE': return 'SAFE';
      default: return 'UNKNOWN';
    }
  };

  const handleAddSubmit = async (e: React.FormEvent, overrideGuardian: boolean = false) => {
    e.preventDefault();
    try {
      const formDataWithOverride = overrideGuardian 
        ? { ...addFormData, override_guardian: true }
        : addFormData;
        
      const result = await apiService.addBlocklistEntry(formDataWithOverride);
      setMessage(result.message || 'IP added successfully');
      setShowAddModal(false);
      setAddFormData({
        ip_address: '',
        time_added: new Date().toISOString().slice(0, 16),
        duration: '24',
        comment: '',
        blocks_count: '1',
        created_by: ''
      });
      setIpValidation(null);
      loadEntries();
    } catch (error: any) {
      const errorData = error.response?.data;
      
      if (errorData?.guardian_block && errorData?.can_override && !overrideGuardian) {
        // Show Guardian warning with override option
        const confidence = Math.round((errorData.confidence || 0) * 100);
        
        setGuardianWarningData({
          riskLevel: errorData.risk_level,
          confidence: confidence,
          reason: errorData.reason?.split('\n')[0] || 'This action may cause infrastructure damage',
          ipAddress: addFormData.ip_address,
          onConfirm: () => {
            setShowGuardianWarning(false);
            setGuardianWarningData(null);
            handleAddSubmit(e, true);
          },
          onCancel: () => {
            setShowGuardianWarning(false);
            setGuardianWarningData(null);
            setMessage(
              `Guardian Protection Active - Risk Level: ${errorData.risk_level} (${confidence}% confidence) - Action cancelled by user. Click the "AI Analysis" button for detailed analysis.`
            );
          }
        });
        setShowGuardianWarning(true);
      } else if (errorData?.guardian_block) {
        // Guardian blocked without override option
        setMessage(
          `Guardian Protection: ${errorData.reason}\n` +
          `Risk Level: ${errorData.risk_level}\n` +
          `This IP was blocked to prevent infrastructure damage.`
        );
      } else {
        setMessage(errorData?.error || 'Failed to add IP');
      }
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentEntry) return;

    try {
      await apiService.updateBlocklistEntry(currentEntry.id, editFormData);
      setMessage('IP updated successfully');
      setShowEditModal(false);
      setCurrentEntry(null);
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to update IP');
    }
  };

  const fillEditForm = (id: number, ip: string, expires: string, comment: string) => {
    const entry = entries.find(e => e.id === id);
    if (entry) {
      setCurrentEntry(entry);
      setEditFormData({
        ip_address: ip,
        time_unblocked: formatToDateTimeLocal(expires),
        comment: comment
      });
      setShowEditModal(true);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;

    try {
      await apiService.deleteBlocklistEntry(id);
      setMessage('Entry deleted successfully');
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to delete entry');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm('Are you sure you want to delete selected entries?')) return;

    try {
      await apiService.bulkDeleteBlocklist(Array.from(selectedIds));
      setMessage(`${selectedIds.size} entries deleted successfully`);
      setSelectedIds(new Set());
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to delete entries');
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(entries.map(entry => entry.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectEntry = (id: number, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const getAIExplanation = async (ipAddress: string) => {
    try {
      const data = await apiService.getAIExplanation(ipAddress);

      // Only show detailed modal for critical risk IPs
      if (data.show_detailed_analysis && data.detailed_explanation) {
        setCurrentExplanation({
          ip: ipAddress,
          explanation: data.detailed_explanation,
          riskLevel: (data.risk_level || 'UNKNOWN').toUpperCase(),
          confidence: data.confidence || 0,
          reasons: data.reasons || [],
          loading: false
        });
        setShowExplanationModal(true);
      } else if (data.simple_message) {
        // For non-critical IPs, just show a simple toast message
        setMessage(`${ipAddress}: ${data.simple_message}`);
      } else {
        // Fallback for other cases
        setMessage(data.fallback_explanation || `AI analysis unavailable for ${ipAddress}`);
      }
    } catch (error) {
      console.error('Failed to get AI explanation:', error);
      setMessage(`Failed to get AI analysis for ${ipAddress}. Please try again later.`);
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await apiService.uploadBlocklistCSV(file);
      setMessage(result.message || 'CSV uploaded successfully');
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to upload CSV');
    }

    // Reset file input
    e.target.value = '';
  };

  const formatToDateTimeLocal = (dateString: string): string => {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    return date.toISOString().slice(0, 16);
  };

  const formatDuration = (hours: number): string => {
    return hours ? `${Math.floor(hours)} hr` : '—';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return <div className="container-fluid mt-5"><div>Loading...</div></div>;
  }

  return (
    <>
      <div className="container-fluid mt-5">
        <div className="row">
          <div className="col-12">
            {/* Guardian Toggle */}
            <GuardianToggle onStatusChange={setGuardianEnabled} />

            {message && (
              <div className="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>{message.split(':')[0]}</strong><br />
                {message.includes(':') && (
                  <ul className="mt-2 mb-0">
                    {message.split(':', 2)[1].split('|').map((err, idx) => (
                      <li key={idx}>{err.trim()}</li>
                    ))}
                  </ul>
                )}
                <button type="button" className="btn-close" onClick={() => setMessage('')} aria-label="Close"></button>
              </div>
            )}

            <h1 className="mb-3">Blocklist Manager</h1>
            
            <div className="mb-3">
              <button 
                id="showFormBtn"
                className="btn btn-primary btn-icon btn-add me-2" 
                onClick={() => setShowAddModal(true)}
              >
                Add IP
              </button>
              <form id="uploadForm" className="d-inline-block" method="POST" action="/blocklist/upload_csv" encType="multipart/form-data">
                <input 
                  type="file" 
                  name="file" 
                  id="csvFile" 
                  accept=".csv" 
                  className="d-none" 
                  required 
                  onChange={handleCSVUpload}
                />
                <button 
                  type="button" 
                  className="btn btn-secondary btn-icon btn-upload" 
                  onClick={() => document.getElementById('csvFile')?.click()}
                >
                  Upload CSV
                </button>
              </form>
            </div>
            
            <hr />

            <div className="d-flex justify-content-between align-items-end mb-3">
              <div>
                <label htmlFor="searchIP" className="form-label">Search</label>
                <div className="d-flex">
                  <input 
                    type="text" 
                    className="form-control w-auto me-2" 
                    id="searchIP"
                    name="search"
                    placeholder="Enter IP/User/Comment"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={handleSearchKeyPress}
                  />
                  <button className="btn btn-secondary btn-icon btn-search" onClick={handleSearch}>Search</button>
                </div>
              </div>
              <div className="text-end">
                <button 
                  id="deleteSelected"
                  className="btn btn-danger btn-icon btn-delete" 
                  disabled={selectedIds.size === 0}
                  onClick={handleBulkDelete}
                >
                  Delete Selected
                </button>
              </div>
            </div>

            <h2>Blocklist Table</h2>
            <div className="table-responsive">
              <table className="table table-bordered table-striped align-middle mb-0" id="blocklistTable">
                <thead className="table-dark">
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        id="selectAll"
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        checked={selectedIds.size === entries.length && entries.length > 0}
                      />
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('ip_address')}
                      >
                        IP Address {getSortIcon('ip_address')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('blocks_count')}
                      >
                        Blocks {getSortIcon('blocks_count')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('added_at')}
                      >
                        Added At {getSortIcon('added_at')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('expires_at')}
                      >
                        Expires At {getSortIcon('expires_at')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('comment')}
                      >
                        Comment {getSortIcon('comment')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('created_by')}
                      >
                        Created By {getSortIcon('created_by')}
                      </button>
                    </th>
                    <th>
                      <button 
                        type="button"
                        className="btn btn-link p-0 text-decoration-none text-dark fw-bold"
                        onClick={() => handleSort('duration')}
                      >
                        Duration {getSortIcon('duration')}
                      </button>
                    </th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.isArray(entries) ? entries.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <input
                          type="checkbox"
                          className="rowCheckbox"
                          data-id={entry.id}
                          checked={selectedIds.has(entry.id)}
                          onChange={(e) => handleSelectEntry(entry.id, e.target.checked)}
                        />
                      </td>
                      <td>{entry.ip_address}</td>
                      <td>{entry.blocks_count}</td>
                      <td>{formatDate(entry.added_at)}</td>
                      <td>{formatDate(entry.expires_at)}</td>
                      <td>{entry.comment}</td>
                      <td>{entry.created_by || '—'}</td>
                      <td>{formatDuration(entry.duration)}</td>
                      <td>
                        {/* Debug logging for critical risk detection */}
                        {entry.ip_address === '8.8.8.8' && (() => {
                          console.log(`DEBUG: 8.8.8.8 found, criticalRiskIPs.has('8.8.8.8'):`, criticalRiskIPs.has('8.8.8.8'), 'criticalRiskIPs:', Array.from(criticalRiskIPs));
                          return null;
                        })()}
                        
                        {criticalRiskIPs.has(entry.ip_address) && (
                          <button
                            type="button"
                            className="btn btn-sm btn-danger rounded-circle me-1"
                            onClick={() => getAIExplanation(entry.ip_address)}
                            title="Critical Risk - Click for detailed analysis"
                            style={{ 
                              width: '32px', 
                              height: '32px', 
                              padding: '0',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '14px',
                              fontWeight: 'bold'
                            }}
                          >
                            !
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-sm btn-warning btn-icon btn-edit me-1"
                          onClick={() => fillEditForm(entry.id, entry.ip_address, entry.expires_at, entry.comment)}
                        >
                          Update
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger btn-icon btn-delete"
                          onClick={() => handleDelete(entry.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={9} className="text-center">No entries found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Add IP Modal */}
      {showAddModal && (
        <div className="modal fade show" id="addIPModal" tabIndex={-1} aria-labelledby="addIPModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <form id="addIPForm" onSubmit={handleAddSubmit}>
                <div className="modal-header">
                  <h5 className="modal-title" id="addIPModalLabel">Add IP to Blocklist</h5>
                  <button type="button" className="btn-close" onClick={() => setShowAddModal(false)}></button>
                </div>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">IP Address</label>
                    <input 
                      type="text" 
                      name="ip_address" 
                      className="form-control" 
                      required
                      value={addFormData.ip_address}
                      onChange={(e) => setAddFormData({...addFormData, ip_address: e.target.value})}
                    />
                    {/* Real-time Guardian Validation */}
                    {guardianEnabled && ipValidation && ipValidation.ip === addFormData.ip_address && (
                      <div className={`mt-2 p-2 rounded ${ipValidation.status.allowed ? 'bg-success' : 'bg-warning'} bg-opacity-10`}>
                        <div className="d-flex align-items-center gap-2">
                          <span style={{ color: getRiskLevelColor(ipValidation.status.risk_level) }}>
                            {getRiskLevelIcon(ipValidation.status.risk_level)}
                          </span>
                          <small className={ipValidation.status.allowed ? 'text-success' : 'text-warning'}>
                            <strong>Guardian:</strong> {ipValidation.status.reason}
                            {ipValidation.status.risk_level && ` (${ipValidation.status.risk_level})`}
                          </small>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Duration (hours)</label>
                    <input 
                      type="number" 
                      name="duration" 
                      className="form-control" 
                      required
                      value={addFormData.duration}
                      onChange={(e) => setAddFormData({...addFormData, duration: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Comment</label>
                    <input 
                      type="text" 
                      name="comment" 
                      className="form-control" 
                      required
                      value={addFormData.comment}
                      onChange={(e) => setAddFormData({...addFormData, comment: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Created By (optional)</label>
                    <input 
                      type="text" 
                      name="created_by" 
                      className="form-control"
                      value={addFormData.created_by}
                      onChange={(e) => setAddFormData({...addFormData, created_by: e.target.value})}
                    />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="submit" className="btn btn-success btn-icon btn-add">Add IP</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {showAddModal && <div className="modal-backdrop fade show"></div>}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="modal fade show" id="editModal" tabIndex={-1} aria-labelledby="editModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <form method="POST" action="/blocklist/update" className="modal-content" onSubmit={handleEditSubmit}>
              <div className="modal-header">
                <h5 className="modal-title" id="editModalLabel">Edit Block Entry</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditModal(false)}></button>
              </div>
              <div className="modal-body">
                <input type="hidden" name="entry_id" id="edit_entry_id" value={currentEntry?.id || ''} />
                <div className="mb-3">
                  <label className="form-label">IP Address</label>
                  <input 
                    type="text" 
                    name="ip_address" 
                    id="edit_ip_address" 
                    className="form-control" 
                    required 
                    readOnly 
                    style={{backgroundColor: '#e9ecef'}}
                    value={editFormData.ip_address}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Time Unblocked</label>
                  <input 
                    type="datetime-local" 
                    name="time_unblocked" 
                    id="edit_time_unblocked" 
                    className="form-control"
                    value={editFormData.time_unblocked}
                    onChange={(e) => setEditFormData({...editFormData, time_unblocked: e.target.value})}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Comment</label>
                  <input 
                    type="text" 
                    name="comment" 
                    id="edit_comment" 
                    className="form-control" 
                    required
                    value={editFormData.comment}
                    onChange={(e) => setEditFormData({...editFormData, comment: e.target.value})}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary btn-icon btn-save">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showEditModal && <div className="modal-backdrop fade show"></div>}

      {/* AI Explanation Modal */}
      {showExplanationModal && currentExplanation && (
        <div className="modal fade show" id="aiExplanationModal" tabIndex={-1} aria-labelledby="aiExplanationModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header" style={{ backgroundColor: 'rgb(0, 48, 135)', color: 'white' }}>
                <h5 className="modal-title" id="aiExplanationModalLabel">
                  AI Analysis: {currentExplanation.ip}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowExplanationModal(false)}></button>
              </div>
              <div className="modal-body">
                {currentExplanation.loading ? (
                  <div className="text-center p-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-2">AI is analyzing the impact of blocking this IP...</p>
                  </div>
                ) : (
                  <div>
                    {/* Risk Level Header */}
                    {currentExplanation.riskLevel !== 'UNKNOWN' && currentExplanation.riskLevel !== 'ERROR' && (
                      <div className="alert border-0 mb-3" style={{ 
                        backgroundColor: currentExplanation.riskLevel === 'CRITICAL' ? '#f8d7da' : 
                                        currentExplanation.riskLevel === 'HIGH' ? '#fff3cd' : '#d1ecf1',
                        borderLeft: `4px solid ${currentExplanation.riskLevel === 'CRITICAL' ? '#dc3545' : 
                                                currentExplanation.riskLevel === 'HIGH' ? '#ff9800' : 'rgb(0, 48, 135)'}`
                      }}>
                        <div className="d-flex align-items-center mb-2">
                          <span className="badge me-3" style={{ 
                            backgroundColor: currentExplanation.riskLevel === 'CRITICAL' ? '#dc3545' : 
                                           currentExplanation.riskLevel === 'HIGH' ? '#ff9800' : 'rgb(0, 48, 135)',
                            color: 'white',
                            fontSize: '0.9em',
                            padding: '8px 12px'
                          }}>
                            {currentExplanation.riskLevel}
                          </span>
                          {currentExplanation.confidence > 0 && (
                            <span className="badge bg-secondary">
                              {Math.round(currentExplanation.confidence * 100)}% Confidence
                            </span>
                          )}
                        </div>
                        <h6 className="alert-heading mb-0">Risk Assessment Complete</h6>
                      </div>
                    )}

                    {/* Network Impact Analysis */}
                    {(currentExplanation as any).network_analysis && (
                      <div className="card mb-3">
                        <div className="card-header bg-light">
                          <h6 className="mb-0">Network Impact Analysis</h6>
                        </div>
                        <div className="card-body">
                          <div className="row">
                            <div className="col-md-6">
                              <div className="text-center p-3 border rounded">
                                <div className="h4 text-primary mb-1">
                                  {((currentExplanation as any).network_analysis.impact_analysis?.addresses_formatted || 
                                    (currentExplanation as any).network_analysis.num_addresses?.toLocaleString() || '1')}
                                </div>
                                <div className="text-muted small">IP Addresses Affected</div>
                              </div>
                            </div>
                            <div className="col-md-6">
                              <div className="text-center p-3 border rounded">
                                <div className="h4 text-info mb-1">
                                  {(currentExplanation as any).network_analysis.impact_analysis?.scope_level || 'SINGLE'}
                                </div>
                                <div className="text-muted small">Impact Scope</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* AI Impact Analysis */}
                    <div className="card mb-3">
                      <div className="card-header bg-light">
                        <h6 className="mb-0">AI-Powered Impact Analysis</h6>
                      </div>
                      <div className="card-body">
                        <div style={{ 
                          whiteSpace: 'pre-wrap', 
                          fontFamily: 'inherit',
                          fontSize: '0.95em',
                          lineHeight: '1.6',
                          color: '#333'
                        }}>
                          {currentExplanation.explanation.replace(/[🔶🌐💼📊🚨⚠️📦]/g, '').trim()}
                        </div>
                      </div>
                    </div>

                    {/* Detection Details */}
                    {currentExplanation.reasons && currentExplanation.reasons.length > 0 && (
                      <div className="card mb-3">
                        <div className="card-header bg-light">
                          <h6 className="mb-0">Detection Details</h6>
                        </div>
                        <div className="card-body">
                          <ul className="list-group list-group-flush">
                            {currentExplanation.reasons.map((reason, index) => (
                              <li key={index} className="list-group-item px-0 border-0">
                                <span className="text-muted">•</span> {reason.replace(/[🚨⚠️📦🔶]/g, '').trim()}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}

                    {/* Technical Details */}
                    {(currentExplanation as any).network_analysis?.impact_analysis && (
                      <div className="card">
                        <div className="card-header bg-light">
                          <h6 className="mb-0">Technical Impact Assessment</h6>
                        </div>
                        <div className="card-body">
                          <div className="row">
                            <div className="col-md-6">
                              <h6 className="text-muted mb-2">Network Classification</h6>
                              <p className="mb-3">{(currentExplanation as any).network_analysis.impact_analysis.network_classification || 'Single IP address'}</p>
                              
                              <h6 className="text-muted mb-2">User Impact</h6>
                              <p className="mb-3">{(currentExplanation as any).network_analysis.impact_analysis.user_impact || 'Could affect 1-10 users'}</p>
                            </div>
                            <div className="col-md-6">
                              <h6 className="text-muted mb-2">Economic Impact</h6>
                              <p className="mb-3">{(currentExplanation as any).network_analysis.impact_analysis.economic_impact || 'Minimal economic impact expected'}</p>
                              
                              <h6 className="text-muted mb-2">Recovery Time</h6>
                              <p className="mb-3">{(currentExplanation as any).network_analysis.impact_analysis.recovery_time || 'Minutes to resolve any issues'}</p>
                            </div>
                          </div>
                          
                          {(currentExplanation as any).network_analysis.impact_analysis?.scope_level && 
                           ['CATASTROPHIC', 'MASSIVE', 'MAJOR'].includes((currentExplanation as any).network_analysis.impact_analysis.scope_level) && (
                            <div className="alert alert-danger border-0 mt-3" style={{ backgroundColor: '#f8d7da', borderLeft: '4px solid #dc3545' }}>
                              <h6 className="alert-heading">High Impact Warning</h6>
                              <p className="mb-0">
                                This action would have a <strong>{(currentExplanation as any).network_analysis.impact_analysis.scope_level.toLowerCase()}</strong> impact 
                                on internet connectivity. Please review carefully before proceeding.
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-icon btn-cancel" onClick={() => setShowExplanationModal(false)}>
                  Close Analysis
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showExplanationModal && <div className="modal-backdrop fade show"></div>}

      {/* Guardian Warning Modal */}
      {showGuardianWarning && guardianWarningData && (
        <div className="modal fade show" id="guardianWarningModal" tabIndex={-1} aria-labelledby="guardianWarningModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header" style={{ backgroundColor: 'rgb(0, 48, 135)', color: 'white' }}>
                <h5 className="modal-title" id="guardianWarningModalLabel">
                  Guardian Protection Warning
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={guardianWarningData.onCancel}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning border-0" style={{ backgroundColor: '#fff3cd', borderLeft: '4px solid #ffc107' }}>
                  <div className="d-flex align-items-center mb-2">
                    <span className="badge me-3" style={{ 
                      backgroundColor: guardianWarningData.riskLevel === 'CRITICAL' ? '#dc3545' : '#ff9800',
                      color: 'white',
                      fontSize: '0.9em',
                      padding: '8px 12px'
                    }}>
                      {guardianWarningData.riskLevel}
                    </span>
                    <span className="badge bg-secondary">
                      {guardianWarningData.confidence}% Confidence
                    </span>
                  </div>
                  <h6 className="alert-heading mb-2">Risk Assessment</h6>
                  <p className="mb-0">{guardianWarningData.reason}</p>
                </div>

                <div className="card mt-3">
                  <div className="card-header bg-light">
                    <h6 className="mb-0">IP Address Under Review</h6>
                  </div>
                  <div className="card-body">
                    <code className="fs-5 text-primary">{guardianWarningData.ipAddress}</code>
                  </div>
                </div>

                <div className="alert alert-info border-0 mt-3" style={{ backgroundColor: '#d1ecf1', borderLeft: '4px solid rgb(0, 48, 135)' }}>
                  <h6 className="alert-heading">Override Options</h6>
                  <p className="mb-2">
                    The Guardian AI has detected potential risks with blocking this IP address. 
                    You can choose to:
                  </p>
                  <ul className="mb-0">
                    <li><strong>Cancel:</strong> Abort the action and review the detailed AI analysis</li>
                    <li><strong>Override:</strong> Proceed with blocking despite the warning</li>
                  </ul>
                </div>
              </div>
              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn btn-secondary btn-icon btn-cancel" 
                  onClick={guardianWarningData.onCancel}
                >
                  Cancel
                </button>
                <button 
                  type="button" 
                  className="btn btn-warning btn-icon" 
                  onClick={guardianWarningData.onConfirm}
                  style={{ backgroundColor: '#ff9800', borderColor: '#ff9800' }}
                >
                  Override Guardian
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showGuardianWarning && <div className="modal-backdrop fade show"></div>}

    </>
  );
};

export default Blocklist; 