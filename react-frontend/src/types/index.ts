// User types
export interface User {
  id: number;
  net_id: string;
  role: string;
  added_at: string;
  token: string;
  active?: boolean;
}

// Blocklist types
export interface BlocklistEntry {
  id: number;
  ip_address: string;
  blocks_count: number;
  added_at: string;
  expires_at: string;
  comment: string;
  created_by: number;
  duration: number; // in hours
}

// Safelist types
export interface SafelistEntry {
  id: number;
  ip_address: string;
  added_at: string;
  expires_at?: string;
  comment: string;
  created_by: number;
  duration: number; // in hours
}

// Dashboard types
export interface DashboardStats {
  total_blocked: number;
  total_safelist: number;
  blocked_today: number;
  blocked_this_week: number;
  blocked_this_month: number;
  peak_hour: string;
  peak_day: string;
}

export interface DashboardData {
  stats: DashboardStats;
  blocks_by_creator: Record<string, number>;
  timeline_data: Record<string, number>;
  ip_distribution: {
    ipv4: number;
    ipv6: number;
  };
  recent_activity: RecentActivity[];
}

export interface RecentActivity {
  added_at: string;
  ip_address: string;
  created_by: string;
}

// API Response types
export interface ApiResponse<T = any> {
  message?: string;
  error?: string;
  data?: T;
}

// Form types
export interface BlocklistFormData {
  ip_address: string;
  time_added: string;
  duration: string;
  comment: string;
  blocks_count: string;
  created_by: string;
  override_guardian?: boolean;
}

export interface SafelistFormData {
  ip_address: string;
  comment: string;
  created_by: string;
  duration: string;
}

export interface SafelistUpdateData {
  ip_address: string;
  comment: string;
  expires_at?: string;
}

export interface UserFormData {
  net_id: string;
  token: string;
  role: string;
}

// Filter types
export interface FilterOptions {
  search?: string;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface DateFilter {
  from?: string;
  to?: string;
} 