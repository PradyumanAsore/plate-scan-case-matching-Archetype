export interface User {
  user_id: number;
  username: string;
  tenant_id: number;
  tenant_name: string;
  role: string;
}

export interface AuthResponse extends User {
  access_token: string;
  token_type: string;
}

export interface Case {
  id: number;
  vin: string;
  status: 'pending_claim' | 'active' | 'closed';
  tenant_id: number | null;
  tenant_name: string | null;
  assigned_agent_id: number | null;
  assigned_agent_username: string | null;
  originating_camera_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CaseListResponse {
  items: Case[];
  total: number;
  limit: number;
  offset: number;
}

export interface Scan {
  id: number;
  camera_id: string;
  camera_description: string | null;
  tenant_name: string | null;
  plate: string;
  vin: string;
  latitude: number;
  longitude: number;
  scanned_at: string;
  image_url: string | null;
  created_at: string;
}

export interface CaseClaimResponse {
  id: number;
  vin: string;
  status: string;
  tenant_id: number;
  assigned_agent_id: number;
  message: string;
}
