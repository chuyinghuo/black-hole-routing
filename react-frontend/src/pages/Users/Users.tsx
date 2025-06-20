import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { User, UserFormData } from '../../types';
import './Users.css';

const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string>('');
  const [messageType, setMessageType] = useState<'success' | 'danger'>('success');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [debouncedRoleFilter, setDebouncedRoleFilter] = useState('');
  const [sortColumn, setSortColumn] = useState('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Form states
  const [addFormData, setAddFormData] = useState<UserFormData>({
    net_id: '',
    token: '',
    role: 'admin'
  });

  const [updateFormData, setUpdateFormData] = useState({
    id: '',
    net_id: '',
    token: '',
    role: 'admin'
  });

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Debounce role filter
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedRoleFilter(roleFilter);
    }, 300);

    return () => clearTimeout(timer);
  }, [roleFilter]);

  useEffect(() => {
    loadUsers();
  }, [debouncedSearchTerm, debouncedRoleFilter, sortColumn, sortOrder]); // loadUsers dependency omitted intentionally

  const loadUsers = async () => {
    try {
      setLoading(true);
      const filters = {
        search: debouncedSearchTerm || undefined,
        sort: sortColumn,
        order: sortOrder
      };
      const data = await apiService.getUsers(filters);
      
      // Filter by role on frontend if role filter is set
      let filteredData = Array.isArray(data) ? data : [];
      if (debouncedRoleFilter) {
        filteredData = filteredData.filter(user => user.role === debouncedRoleFilter);
      }
      
      setUsers(filteredData);
    } catch (error) {
      console.error('Error loading users:', error);
      setMessage('Error loading users');
      setMessageType('danger');
      setUsers([]); // Ensure users is always an array
    } finally {
      setLoading(false);
    }
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (!addFormData.net_id || !addFormData.token || addFormData.token.length < 32) {
        setMessage('Fill all fields. Token must be at least 32 characters.');
        setMessageType('danger');
        return;
      }
      
      await apiService.addUser(addFormData);
      setMessage('User added successfully');
      setMessageType('success');
      setShowAddModal(false);
      setAddFormData({ net_id: '', token: '', role: 'admin' });
      loadUsers();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to add user');
      setMessageType('danger');
    }
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!window.confirm('Are you sure you want to update this user?')) return;
    
    try {
      if (!updateFormData.token || updateFormData.token.length < 32) {
        setMessage('Token must be at least 32 characters.');
        setMessageType('danger');
        return;
      }
      
      await apiService.updateUser(parseInt(updateFormData.id), {
        net_id: updateFormData.net_id,
        token: updateFormData.token,
        role: updateFormData.role
      });
      setMessage('User updated successfully');
      setMessageType('success');
      setShowUpdateModal(false);
      loadUsers();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to update user');
      setMessageType('danger');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to deactivate this user?')) return;
    
    try {
      await apiService.deleteUser(id);
      setMessage('User deactivated successfully');
      setMessageType('success');
      loadUsers();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to deactivate user');
      setMessageType('danger');
    }
  };

  const handleReinstate = async (id: number) => {
    if (!window.confirm('Are you sure you want to reinstate this user?')) return;
    
    try {
      await apiService.reinstateUser(id);
      setMessage('User reinstated successfully');
      setMessageType('success');
      loadUsers();
    } catch (error: any) {
      setMessage(error.response?.data?.error || 'Failed to reinstate user');
      setMessageType('danger');
    }
  };

  const fillUpdateForm = (user: User) => {
    setUpdateFormData({
      id: user.id.toString(),
      net_id: user.net_id,
      token: user.token,
      role: user.role
    });
    setShowUpdateModal(true);
  };

  const setSort = (field: string) => {
    if (sortColumn === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(field);
      setSortOrder('asc');
    }
  };

  const getSortIndicator = (field: string) => {
    if (sortColumn !== field) return '';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  const capitalize = (word: string) => {
    return word.charAt(0).toUpperCase() + word.slice(1);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="container-fluid mt-5">
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <>
      <div className="container-fluid mt-5">
        <div className="row">
          <div className="col-12">
            <h1 className="mb-4">User Management</h1>
            
            {/* Search, Filter, Add User Row */}
            <div className="d-flex justify-content-between align-items-end mb-3">
              <div className="d-flex align-items-end">
                <div className="me-2">
                  <label htmlFor="searchInput" className="form-label">Search by Net ID</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    id="searchInput" 
                    placeholder="Enter Net ID"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="me-2">
                  <label htmlFor="roleFilter" className="form-label">Filter by Role</label>
                  <select 
                    className="form-select" 
                    id="roleFilter"
                    value={roleFilter}
                    onChange={(e) => setRoleFilter(e.target.value)}
                  >
                    <option value="">All Roles</option>
                    <option value="admin">Admin</option>
                    <option value="editor">Editor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>

              </div>
              <button 
                id="showFormBtn" 
                className="btn btn-primary me-2" 
                onClick={() => setShowAddModal(true)}
              >
                Add User
              </button>
            </div>
            
            {message && <p id="message" className={`fw-bold text-${messageType}`}>{message}</p>}
            
            <h2 id="userListTitle">All {roleFilter ? capitalize(roleFilter) + 's' : 'Users'}</h2>
            
            <div className="table-responsive">
              <table className="table table-bordered table-striped align-middle" id="usersTable">
                <thead className="table-dark">
                  <tr>
                    <th>
                      <a href="#" onClick={(e) => { e.preventDefault(); setSort('id'); }}>
                        ID <span id="sort-id">{getSortIndicator('id')}</span>
                      </a>
                    </th>
                    <th>
                      <a href="#" onClick={(e) => { e.preventDefault(); setSort('net_id'); }}>
                        Net ID <span id="sort-net_id">{getSortIndicator('net_id')}</span>
                      </a>
                    </th>
                    <th>
                      <a href="#" onClick={(e) => { e.preventDefault(); setSort('role'); }}>
                        Role <span id="sort-role">{getSortIndicator('role')}</span>
                      </a>
                    </th>
                    <th>
                      <a href="#" onClick={(e) => { e.preventDefault(); setSort('added_at'); }}>
                        Time Added <span id="sort-added_at">{getSortIndicator('added_at')}</span>
                      </a>
                    </th>
                    <th>Token</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.isArray(users) ? users.map((user) => (
                    <tr key={user.id} className={!user.active ? 'table-secondary' : ''}>
                      <td>{user.id}</td>
                      <td>{user.net_id}</td>
                      <td>{user.role}</td>
                      <td>{formatDate(user.added_at)}</td>
                      <td className="text-truncate" style={{maxWidth: '300px'}}>{user.token}</td>
                      <td>
                        <span className={`badge ${user.active ? 'bg-success' : 'bg-secondary'}`}>
                          {user.active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-warning me-1" 
                          onClick={() => fillUpdateForm(user)}
                          disabled={!user.active}
                        >
                          Update
                        </button>
                        {user.active ? (
                          <button 
                            className="btn btn-sm btn-danger" 
                            onClick={() => handleDelete(user.id)}
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button 
                            className="btn btn-sm btn-success" 
                            onClick={() => handleReinstate(user.id)}
                          >
                            Reinstate
                          </button>
                        )}
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={7} className="text-center">No users found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Pagination would go here */}
            <div className="mt-3 d-flex justify-content-center" id="pagination"></div>
          </div>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="modal fade show" id="addUserModal" tabIndex={-1} aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <form id="userForm" className="modal-content" onSubmit={handleAddSubmit}>
              <div className="modal-header">
                <h5 className="modal-title">Add User</h5>
                <button type="button" className="btn-close" onClick={() => setShowAddModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label htmlFor="net_id" className="form-label">Net ID</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    id="net_id" 
                    required
                    value={addFormData.net_id}
                    onChange={(e) => setAddFormData({...addFormData, net_id: e.target.value})}
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="token" className="form-label">Token (min 32 chars)</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    id="token" 
                    required
                    value={addFormData.token}
                    onChange={(e) => setAddFormData({...addFormData, token: e.target.value})}
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="role" className="form-label">Role</label>
                  <select 
                    className="form-select" 
                    id="role" 
                    required
                    value={addFormData.role}
                    onChange={(e) => setAddFormData({...addFormData, role: e.target.value})}
                  >
                    <option value="admin">Admin</option>
                    <option value="editor">Editor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">Add User</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showAddModal && <div className="modal-backdrop fade show"></div>}

      {/* Update Modal */}
      {showUpdateModal && (
        <div className="modal fade show" id="updateModal" tabIndex={-1} aria-hidden="true" style={{ display: 'block' }}>
          <div className="modal-dialog">
            <form id="updateForm" className="modal-content" onSubmit={handleUpdateSubmit}>
              <div className="modal-header">
                <h5 className="modal-title">Update User</h5>
                <button type="button" className="btn-close" onClick={() => setShowUpdateModal(false)}></button>
              </div>
              <div className="modal-body">
                <input type="hidden" id="updateId" value={updateFormData.id} />
                <div className="mb-3">
                  <label htmlFor="updateNetId" className="form-label">Net ID</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    id="updateNetId" 
                    disabled
                    value={updateFormData.net_id}
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="updateToken" className="form-label">Token</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    id="updateToken" 
                    required
                    value={updateFormData.token}
                    onChange={(e) => setUpdateFormData({...updateFormData, token: e.target.value})}
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="updateRole" className="form-label">Role</label>
                  <select 
                    className="form-select" 
                    id="updateRole" 
                    required
                    value={updateFormData.role}
                    onChange={(e) => setUpdateFormData({...updateFormData, role: e.target.value})}
                  >
                    <option value="admin">Admin</option>
                    <option value="editor">Editor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showUpdateModal && <div className="modal-backdrop fade show"></div>}
    </>
  );
};

export default Users; 