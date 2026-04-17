/**
 * PCB Builder - API Client
 */

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  register(data: { email: string; password: string; full_name: string }) {
    return this.request('/auth/register', { method: 'POST', body: JSON.stringify(data) });
  }

  login(data: { email: string; password: string }) {
    return this.request('/auth/login', { method: 'POST', body: JSON.stringify(data) });
  }

  getProfile() {
    return this.request('/auth/me');
  }

  // Projects
  listProjects() {
    return this.request('/projects/');
  }

  createProject(data: { name: string; description?: string }) {
    return this.request('/projects/', { method: 'POST', body: JSON.stringify(data) });
  }

  getProject(id: string) {
    return this.request(`/projects/${id}`);
  }

  // Designs
  createDesign(projectId: string, data: { name: string; board_config?: Record<string, unknown> }) {
    return this.request(`/projects/${projectId}/designs`, {
      method: 'POST',
      body: JSON.stringify({ ...data, project_id: projectId }),
    });
  }

  getDesign(projectId: string, designId: string) {
    return this.request(`/projects/${projectId}/designs/${designId}`);
  }

  updateDesign(projectId: string, designId: string, data: Record<string, unknown>) {
    return this.request(`/projects/${projectId}/designs/${designId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // AI
  parseIntent(data: { user_input: string; design_context?: Record<string, unknown> }) {
    return this.request('/ai/parse-intent', { method: 'POST', body: JSON.stringify(data) });
  }

  chat(data: { design_id: string; message: string; context?: Record<string, unknown> }) {
    return this.request('/ai/chat', { method: 'POST', body: JSON.stringify(data) });
  }

  autoFix(data: { violations: Record<string, unknown>[]; design_data: Record<string, unknown> }) {
    return this.request('/ai/auto-fix', { method: 'POST', body: JSON.stringify(data) });
  }

  designReview(data: { design_data: Record<string, unknown>; review_type?: string }) {
    return this.request('/ai/design-review', { method: 'POST', body: JSON.stringify(data) });
  }

  // EDA
  runDRC(data: { design_data: Record<string, unknown>; rules?: Record<string, unknown> }) {
    return this.request('/eda/drc', { method: 'POST', body: JSON.stringify(data) });
  }

  generateGerber(designId: string) {
    return this.request('/eda/generate-gerber', {
      method: 'POST',
      body: JSON.stringify({ design_id: designId }),
    });
  }

  getJobStatus(jobId: string) {
    return this.request(`/eda/job/${jobId}`);
  }

  searchComponents(data: { query: string; category?: string; limit?: number }) {
    return this.request('/eda/components/search', { method: 'POST', body: JSON.stringify(data) });
  }

  // Fabrication
  getQuotes(data: { design_id: string; options?: Record<string, unknown>; prefer_indian?: boolean }) {
    return this.request('/fab/quotes', { method: 'POST', body: JSON.stringify(data) });
  }

  listFabricators() {
    return this.request('/fab/fabricators');
  }
}

export const api = new ApiClient();
