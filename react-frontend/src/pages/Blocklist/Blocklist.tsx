import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { BlocklistEntry, BlocklistFormData, FilterOptions } from '../../types';
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

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await apiService.addBlocklistEntry(addFormData);
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
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to add IP');
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
    const newSelectedIds = new Set(selectedIds);
    if (checked) {
      newSelectedIds.add(id);
    } else {
      newSelectedIds.delete(id);
    }
    setSelectedIds(newSelectedIds);
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
                className="btn btn-primary me-2" 
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
                  className="btn btn-secondary" 
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
                  <button className="btn btn-secondary" onClick={handleSearch}>Search</button>
                </div>
              </div>
              <div className="text-end">
                <button 
                  id="deleteSelected"
                  className="btn btn-danger" 
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
                          className="btn btn-sm btn-warning updateBtn me-1"
                          onClick={() => fillEditForm(entry.id, entry.ip_address, entry.expires_at, entry.comment)}
                        >
                          Update
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
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
                  <button type="submit" className="btn btn-success">➕ Add IP</button>
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
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showEditModal && <div className="modal-backdrop fade show"></div>}
    </>
  );
};

export default Blocklist; 