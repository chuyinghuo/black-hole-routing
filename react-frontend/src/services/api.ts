import axios, { AxiosResponse } from 'axios';
import {
  BlocklistEntry,
  SafelistEntry,
  User,
  DashboardData,
  ApiResponse,
  BlocklistFormData,
  SafelistFormData,
  UserFormData,
  FilterOptions,
  DateFilter
} from '../types';

// Configure axios base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Add request/response interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

class ApiService {
  // Dashboard API
  async getDashboardData(): Promise<DashboardData> {
    const response: AxiosResponse<DashboardData> = await apiClient.get('/dashboard/data');
    return response.data;
  }

  async filterStats(type: string, filter: DateFilter): Promise<{ count: number }> {
    const response = await apiClient.get('/dashboard/api/filter_stats', {
      params: {
        type,
        from: filter.from,
        to: filter.to
      }
    });
    return response.data;
  }

  // Blocklist API
  async getBlocklistEntries(filters?: FilterOptions): Promise<BlocklistEntry[]> {
    const params = new URLSearchParams();
    if (filters?.search) params.append('search', filters.search);
    if (filters?.sort) params.append('sort', filters.sort);
    if (filters?.order) params.append('order', filters.order);

    const response = await apiClient.get(`/blocklist?${params.toString()}`);
    return response.data;
  }

  async addBlocklistEntry(data: BlocklistFormData): Promise<ApiResponse> {
    const response = await apiClient.post('/blocklist/', data);
    return response.data;
  }

  async updateBlocklistEntry(entryId: number, data: Partial<BlocklistFormData>): Promise<ApiResponse> {
    const response = await apiClient.post('/blocklist/update', {
      entry_id: entryId,
      ...data
    }, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async deleteBlocklistEntry(entryId: number): Promise<ApiResponse> {
    const response = await apiClient.post('/blocklist/delete', {
      entry_id: entryId
    }, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async bulkDeleteBlocklist(entryIds: number[]): Promise<ApiResponse> {
    const response = await apiClient.post('/blocklist/delete_bulk', {
      ids: entryIds
    }, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async uploadBlocklistCSV(file: File): Promise<ApiResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/blocklist/upload_csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }

  async searchBlocklistIP(ip: string): Promise<BlocklistEntry[]> {
    const response = await apiClient.get(`/blocklist/search?ip=${encodeURIComponent(ip)}`);
    return response.data;
  }

  // Safelist API
  async getSafelistEntries(filters?: FilterOptions): Promise<SafelistEntry[]> {
    const params = new URLSearchParams();
    if (filters?.search) params.append('search', filters.search);
    if (filters?.sort) params.append('sort', filters.sort);
    if (filters?.order) params.append('order', filters.order);

    const response = await apiClient.get(`/safelist/api/safelist?${params.toString()}`);
    return response.data.entries || []; // Extract entries array from response
  }

  async addSafelistEntry(data: SafelistFormData): Promise<ApiResponse> {
    const response = await apiClient.post('/safelist/api/safelist', data, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async updateSafelistEntry(entryId: number, data: Partial<SafelistFormData>): Promise<ApiResponse> {
    const response = await apiClient.put(`/safelist/api/safelist/${entryId}`, data, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async deleteSafelistEntry(entryId: number): Promise<ApiResponse> {
    const response = await apiClient.delete(`/safelist/api/safelist/${entryId}`);
    return response.data;
  }

  async uploadSafelistCSV(file: File): Promise<ApiResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/safelist/api/safelist/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }

  async searchSafelistIP(ip: string): Promise<SafelistEntry[]> {
    const response = await apiClient.get(`/safelist/search?ip=${encodeURIComponent(ip)}`);
    return response.data;
  }

  // Users API
  async getUsers(filters?: FilterOptions): Promise<User[]> {
    const params = new URLSearchParams();
    if (filters?.search) params.append('search', filters.search);
    if (filters?.sort) params.append('sort', filters.sort);
    if (filters?.order) params.append('order', filters.order);

    const response = await apiClient.get(`/users/users?${params.toString()}`);
    return response.data.users || []; // Extract users array from paginated response
  }

  async addUser(data: UserFormData): Promise<ApiResponse> {
    const response = await apiClient.post('/users/add-user', data);
    return response.data;
  }

  async updateUser(userId: number, data: Partial<UserFormData>): Promise<ApiResponse> {
    const response = await apiClient.put(`/users/edit/user/${userId}`, data, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  }

  async deleteUser(userId: number): Promise<ApiResponse> {
    const response = await apiClient.delete(`/users/remove-user/${userId}`);
    return response.data;
  }

  async reinstateUser(userId: number): Promise<ApiResponse> {
    const response = await apiClient.post(`/users/reinstate-user/${userId}`);
    return response.data;
  }

  async searchUsers(query: string): Promise<User[]> {
    const response = await apiClient.get(`/users/search?q=${encodeURIComponent(query)}`);
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await apiClient.get('/health');
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService; 