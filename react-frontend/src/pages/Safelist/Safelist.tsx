import React, { useState, useEffect } from 'react';
import { Container } from 'react-bootstrap';
import { apiService } from '../../services/api';
import { SafelistEntry, SafelistFormData, FilterOptions } from '../../types';
import './Safelist.css';

const Safelist: React.FC = () => {
  const [entries, setEntries] = useState<SafelistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string>('');
  const [showAddModal, setShowAddModal] = useState(false);

  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState('added_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateFormData, setUpdateFormData] = useState({
    id: '',
    ip_address: '',
    comment: '',
    expires_at: ''
  });

  // Form states
  const [addFormData, setAddFormData] = useState<SafelistFormData>({
    ip_address: '',
    comment: '',
    created_by: '',
    duration: ''
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
  }, [sortColumn, sortOrder, debouncedSearchTerm]); // loadEntries dependency omitted intentionally

  const loadEntries = async () => {
    try {
      setLoading(true);
      const filters: FilterOptions = {
        search: debouncedSearchTerm || undefined,
        sort: sortColumn,
        order: sortOrder
      };
      const data = await apiService.getSafelistEntries(filters);
      setEntries(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading safelist entries:', error);
      setMessage('Error loading safelist entries');
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
      handleSearch();
    }
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await apiService.addSafelistEntry(addFormData);
      setMessage(result.message || 'IP added to safelist successfully');
      setShowAddModal(false);
      setAddFormData({
        ip_address: '',
        comment: '',
        created_by: '',
        duration: ''
      });
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to add IP to safelist');
    }
  };



  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;

    try {
      await apiService.deleteSafelistEntry(id);
      setMessage('Safelist entry deleted successfully');
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to delete safelist entry');
    }
  };

  const formatToDateTimeLocal = (dateString: string): string => {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    return date.toISOString().slice(0, 16);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await apiService.uploadSafelistCSV(file);
      setMessage(result.message || 'CSV uploaded successfully');
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to upload CSV');
    }
  };

  const searchIP = () => {
    loadEntries();
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedIds.size} selected entries?`)) return;

    try {
      await Promise.all(Array.from(selectedIds).map(id => apiService.deleteSafelistEntry(id)));
      setMessage(`${selectedIds.size} entries deleted successfully`);
      setSelectedIds(new Set());
      loadEntries();
    } catch (error: any) {
      setMessage('Failed to delete some entries');
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

  const setSort = (field: string) => {
    handleSort(field);
  };

  const getSortIndicator = (field: string) => {
    return getSortIcon(field);
  };

  const fillUpdateForm = (entry: SafelistEntry) => {
    setUpdateFormData({
      id: entry.id.toString(),
      ip_address: entry.ip_address,
      comment: entry.comment || '',
      expires_at: entry.expires_at ? formatToDateTimeLocal(entry.expires_at) : ''
    });
    setShowUpdateModal(true);
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiService.updateSafelistEntry(parseInt(updateFormData.id), {
        ip_address: updateFormData.ip_address,
        comment: updateFormData.comment,
        expires_at: updateFormData.expires_at
      });
      setMessage('Entry updated successfully');
      setShowUpdateModal(false);
      loadEntries();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to update entry');
    }
  };

  if (loading) {
    return <Container className="mt-5"><div>Loading...</div></Container>;
  }

  return (
    <>
      <div className="container-fluid mt-5">
        <div className="row">
          <div className="col-12">
            <h1 className="mb-3">Safelist Manager</h1>

            <div className="mb-3">
              <button 
                id="showFormBtn" 
                className="btn btn-primary me-2" 
                onClick={() => setShowAddModal(true)}
              >
                Add IP
              </button>

              <form id="uploadForm" className="d-inline-block" encType="multipart/form-data">
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
            
            {message && <div id="message" className="mb-4 text-success fw-bold">{message}</div>}


            <div className="d-flex justify-content-between align-items-end mb-3">
              <div>
                <label htmlFor="searchField" className="form-label">Search</label>
                <div className="d-flex">
                  <input 
                    type="text" 
                    className="form-control w-auto me-2" 
                    id="searchIP" 
                    placeholder="Enter IP/User/Comment"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={handleSearchKeyPress}
                  />
                  <button className="btn btn-secondary" onClick={searchIP}>Search</button>
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

            <h2>Safelist Table</h2>
            <table className="table table-bordered table-striped" id="ipTable">
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
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('id'); }}>
                      ID <span id="sort-id">{getSortIndicator('id')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('ip_address'); }}>
                      IP Address <span id="sort-ip_address">{getSortIndicator('ip_address')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('comment'); }}>
                      Comment <span id="sort-comment">{getSortIndicator('comment')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('created_by'); }}>
                      Created By <span id="sort-created_by">{getSortIndicator('created_by')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('added_at'); }}>
                      Added At <span id="sort-added_at">{getSortIndicator('added_at')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('expires_at'); }}>
                      Expires At <span id="sort-expires_at">{getSortIndicator('expires_at')}</span>
                    </a>
                  </th>
                  <th>
                    <a href="#" onClick={(e) => { e.preventDefault(); setSort('duration'); }}>
                      Duration (hrs) <span id="sort-duration">{getSortIndicator('duration')}</span>
                    </a>
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
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
                    <td>{entry.id}</td>
                    <td>{entry.ip_address}</td>
                    <td>{entry.comment || ''}</td>
                    <td>{entry.created_by || ''}</td>
                    <td>{formatDate(entry.added_at)}</td>
                    <td>{entry.expires_at ? formatDate(entry.expires_at) : ''}</td>
                    <td>{entry.duration ? parseFloat(entry.duration.toString()).toFixed(2) : ''}</td>
                    <td>
                      <button 
                        className="btn btn-sm btn-warning updateBtn me-1" 
                        onClick={() => fillUpdateForm(entry)}
                      >
                        Update
                      </button>
                      <button 
                        className="btn btn-sm btn-danger" 
                        onClick={() => handleDelete(entry.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination would go here */}
          </div>
        </div>
      </div>

      {/* Add IP Modal */}
      {showAddModal && (
        <div className="modal fade show" id="addIpModal" tabIndex={-1} aria-labelledby="addIpModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <form id="ipForm" onSubmit={handleAddSubmit}>
                <div className="modal-header">
                  <h5 className="modal-title" id="addIpModalLabel">Add IP to Safelist</h5>
                  <button type="button" className="btn-close" onClick={() => setShowAddModal(false)} aria-label="Close"></button>
                </div>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="ip_address" className="form-label">IP Address</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      id="ip_address" 
                      placeholder="e.g. 192.168.1.1 or 192.168.1.0/24" 
                      required
                      value={addFormData.ip_address}
                      onChange={(e) => setAddFormData({...addFormData, ip_address: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="comment" className="form-label">Comment</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      id="comment" 
                      placeholder="Optional comment"
                      value={addFormData.comment}
                      onChange={(e) => setAddFormData({...addFormData, comment: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="duration" className="form-label">Duration (hrs)</label>
                    <input 
                      type="number" 
                      className="form-control" 
                      id="duration" 
                      placeholder="e.g. 24" 
                      required 
                      min="1"
                      value={addFormData.duration}
                      onChange={(e) => setAddFormData({...addFormData, duration: e.target.value})}
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

      {/* Update Modal */}
      {showUpdateModal && (
        <div className="modal fade show" id="updateModal" tabIndex={-1} aria-labelledby="updateModalLabel" aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <form id="updateForm" onSubmit={handleUpdateSubmit}>
                <div className="modal-header">
                  <h5 className="modal-title" id="updateModalLabel">Update IP Entry</h5>
                  <button type="button" className="btn-close" onClick={() => setShowUpdateModal(false)} aria-label="Close"></button>
                </div>
                <div className="modal-body">
                  <input type="hidden" id="updateId" value={updateFormData.id} />
                  <div className="mb-3">
                    <label htmlFor="updateIP" className="form-label">IP Address</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      id="updateIP" 
                      required
                      value={updateFormData.ip_address}
                      onChange={(e) => setUpdateFormData({...updateFormData, ip_address: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="updateComment" className="form-label">Comment</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      id="updateComment"
                      value={updateFormData.comment}
                      onChange={(e) => setUpdateFormData({...updateFormData, comment: e.target.value})}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="updateEnding" className="form-label">Expires At</label>
                    <input 
                      type="datetime-local" 
                      className="form-control" 
                      id="updateEnding"
                      value={updateFormData.expires_at}
                      onChange={(e) => setUpdateFormData({...updateFormData, expires_at: e.target.value})}
                    />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="submit" className="btn btn-primary">Save Changes</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {showUpdateModal && <div className="modal-backdrop fade show"></div>}
    </>
  );
};

export default Safelist; 