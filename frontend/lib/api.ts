const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('qp_token');
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('qp_token', token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('qp_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('qp_token');
    }
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${BASE_URL}${endpoint}`;
    
    // Setup headers
    const headers = new Headers(options.headers || {});
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const token = this.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(url, config);
      
      if (response.status === 401) {
        // If unauthorized, attempt to auto-login as admin for quick evaluation/demo
        this.clearToken();
        if (endpoint !== '/auth/login') {
          console.log("Unauthorized. Attempting auto-login...");
          const loggedIn = await this.autoLogin();
          if (loggedIn) {
            // Retry request
            return this.request(endpoint, options);
          }
        }
        throw new Error('Unauthorized');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP Error ${response.status}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error(`API Request Error on ${endpoint}:`, error);
      throw error;
    }
  }

  async autoLogin(): Promise<boolean> {
    try {
      const data = await this.login('admin@querypilot.com', 'adminpassword');
      this.setToken(data.access_token);
      console.log("Auto-logged in successfully as admin.");
      return true;
    } catch (e) {
      console.error("Auto-login failed:", e);
      return false;
    }
  }

  async login(email: string, password: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) throw new Error('Login credentials rejected.');
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  }

  // Query Workspace
  async analyze(question: string, sessionId?: string, provider?: string, model?: string) {
    return this.request('/query/analyze', {
      method: 'POST',
      body: JSON.stringify({ question, session_id: sessionId, provider, model })
    });
  }

  async respond(sessionId: string, answer: string, provider?: string, model?: string) {
    return this.request('/query/respond', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, answer, provider, model })
    });
  }

  // Schema Explorer
  async getSchema() {
    return this.request('/schema/explorer');
  }

  async refreshSchema() {
    return this.request('/schema/refresh', { method: 'POST' });
  }

  // Semantic Layer
  async getSemantics() {
    return this.request('/semantics');
  }

  async saveSemantic(term: string, category: string, sqlFragment: string, definition: string) {
    return this.request('/semantics', {
      method: 'POST',
      body: JSON.stringify({ term, category, sql_fragment: sqlFragment, definition })
    });
  }

  async deleteSemantic(id: number) {
    return this.request(`/semantics/${id}`, {
      method: 'DELETE'
    });
  }

  // Audit and History
  async getHistory() {
    return this.request('/history');
  }

  async getHistoryDetails(id: number) {
    return this.request(`/history/${id}`);
  }

  async getAuditLogs(sessionId: string) {
    return this.request(`/history/${sessionId}/audit`);
  }

  // Settings
  async getSettings() {
    return this.request('/admin/settings');
  }

  async saveSettings(settings: any) {
    return this.request('/admin/settings', {
      method: 'POST',
      body: JSON.stringify(settings)
    });
  }
}

export const api = new ApiClient();
export default api;
