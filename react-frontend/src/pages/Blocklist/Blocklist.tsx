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
  const [showExplanationModal, setShowExplanationModal] = useState(false);
  const [currentExplanation, setCurrentExplanation] = useState<{
    ip: string;
    explanation: string;
    riskLevel: string;
    confidence: number;
    reasons: string[];
    loading: boolean;
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
    } catch (error) {
      console.error('Error loading blocklist entries:', error);
      setMessage('Error loading blocklist entries');
      setEntries([]); // Ensure entries is always an array
    } finally {
      setLoading(false);
    }
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
        
        const userConfirmed = window.confirm(
          `GUARDIAN AI WARNING\n\n` +
          `Risk Level: ${errorData.risk_level} (${confidence}% confidence)\n\n` +
          `WARNING: ${errorData.reason?.split('\n')[0] || 'This action may cause infrastructure damage'}\n\n` +
          `Are you sure you want to proceed?\n` +
          `Click OK to override the Guardian and add this IP anyway.\n` +
          `Click Cancel to abort and review the AI analysis.`
        );
        
        if (userConfirmed) {
          // User chose to override - retry with override flag
          handleAddSubmit(e, true);
        } else {
          // User cancelled - show the detailed explanation
          setMessage(
            `Guardian Protection Active\n` +
            `Risk Level: ${errorData.risk_level} (${confidence}% confidence)\n` +
            `Action cancelled by user. Click the "AI Analysis" button for detailed analysis.`
          );
        }
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
    setCurrentExplanation({
      ip: ipAddress,
      explanation: '',
      riskLevel: '',
      confidence: 0,
      reasons: [],
      loading: true
    });
    setShowExplanationModal(true);

    try {
      const data = await apiService.getAIExplanation(ipAddress);

      if (data.detailed_explanation) {
        setCurrentExplanation({
          ip: ipAddress,
          explanation: data.detailed_explanation,
          riskLevel: (data.risk_level || 'UNKNOWN').toUpperCase(),
          confidence: data.confidence || 0,
          reasons: data.reasons || [],
          loading: false
        });
      } else {
        setCurrentExplanation({
          ip: ipAddress,
          explanation: data.fallback_explanation || 'No detailed explanation available.',
          riskLevel: 'UNKNOWN',
          confidence: 0,
          reasons: [],
          loading: false
        });
      }
    } catch (error) {
      console.error('Failed to get AI explanation:', error);
      setCurrentExplanation({
        ip: ipAddress,
        explanation: 'Failed to get AI explanation. Please try again later.',
        riskLevel: 'ERROR',
        confidence: 0,
        reasons: [],
        loading: false
      });
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
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('ip_address'); }}
                      >
                        IP Address {getSortIcon('ip_address')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('blocks_count'); }}
                      >
                        Blocks {getSortIcon('blocks_count')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('added_at'); }}
                      >
                        Added At {getSortIcon('added_at')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('expires_at'); }}
                      >
                        Expires At {getSortIcon('expires_at')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('comment'); }}
                      >
                        Comment {getSortIcon('comment')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('created_by'); }}
                      >
                        Created By {getSortIcon('created_by')}
                      </a>
                    </th>
                    <th>
                      <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); handleSort('duration'); }}
                      >
                        Duration {getSortIcon('duration')}
                      </a>
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
                        <button
                          type="button"
                          className="btn btn-sm btn-info btn-icon btn-ai me-1"
                          onClick={() => getAIExplanation(entry.ip_address)}
                          title="Get AI explanation about blocking this IP"
                        >
                          AI Analysis
                        </button>
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
              <div className="modal-header">
                <h5 className="modal-title" id="aiExplanationModalLabel">
                  AI Analysis: {currentExplanation.ip}
                </h5>
                <button type="button" className="btn-close" onClick={() => setShowExplanationModal(false)}></button>
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
                      <div className="alert alert-info d-flex align-items-center mb-3">
                        <span className="me-2" style={{ fontSize: '1.5em' }}>
                          {getRiskLevelIcon(currentExplanation.riskLevel)}
                        </span>
                        <div>
                          <strong>Risk Level: {currentExplanation.riskLevel}</strong>
                          {currentExplanation.confidence > 0 && (
                            <span className="ms-2 badge bg-secondary">
                              {Math.round(currentExplanation.confidence * 100)}% Confidence
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* AI Explanation */}
                    <div className="card">
                      <div className="card-header">
                        <h6 className="mb-0">AI-Powered Impact Analysis</h6>
                      </div>
                      <div className="card-body">
                        <pre style={{ 
                          whiteSpace: 'pre-wrap', 
                          fontFamily: 'inherit',
                          fontSize: '0.9em',
                          margin: 0,
                          background: 'none',
                          border: 'none'
                        }}>
                          {currentExplanation.explanation}
                        </pre>
                      </div>
                    </div>

                    {/* Raw Reasons (if available) */}
                    {currentExplanation.reasons && currentExplanation.reasons.length > 0 && (
                      <div className="card mt-3">
                        <div className="card-header">
                          <h6 className="mb-0">Detection Details</h6>
                        </div>
                        <div className="card-body">
                          <ul className="list-group list-group-flush">
                            {currentExplanation.reasons.map((reason, index) => (
                              <li key={index} className="list-group-item px-0">
                                <small>{reason}</small>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary btn-icon btn-cancel" onClick={() => setShowExplanationModal(false)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showExplanationModal && <div className="modal-backdrop fade show"></div>}
    </>
  );
};

export default Blocklist; 