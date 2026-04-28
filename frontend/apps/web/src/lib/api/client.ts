/**
 * PCB Builder - Production API Client
 * With retry logic, error handling, and structured responses.
 */

import type { Project } from '../../stores';

const API_BASE = '/api/v1';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(path: string, options: RequestInit = {}, retryCount = 0): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          error_code: `HTTP_${response.status}`,
          message: `Request failed with status ${response.status}`,
          suggestion: 'Please try again or contact support if the issue persists.',
        }));

        // Retry on 5xx errors or rate limit
        if ((response.status >= 500 || response.status === 429) && retryCount < MAX_RETRIES) {
          const delay = RETRY_DELAY_MS * Math.pow(2, retryCount);
          const retryAfter = response.headers.get('Retry-After');
          await sleep(retryAfter ? parseInt(retryAfter) * 1000 : delay);
          return this.request(path, options, retryCount + 1);
        }

        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      return response.json();
    } catch (err: any) {
      // Network errors - retry
      if (retryCount < MAX_RETRIES && (err.name === 'TypeError' || err.name === 'NetworkError')) {
        await sleep(RETRY_DELAY_MS * Math.pow(2, retryCount));
        return this.request(path, options, retryCount + 1);
      }
      throw err;
    }
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
  async listProjects() {
    const data = await this.request<Project[] | { items: Project[] }>('/projects/');
    if (Array.isArray(data)) return { items: data };
    return data;
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
  generatePCB(data: {
    input_type: string;
    description?: string;
    components?: Record<string, unknown>[];
    nets?: Record<string, unknown>[];
    board_config?: Record<string, unknown>;
  }) {
    return this.request('/ai/generate-pcb', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  getJobStatus(jobId: string) {
    return this.request(`/ai/jobs/${jobId}`);
  }

  listJobs(page = 1, pageSize = 20, status?: string) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.append('status', status);
    return this.request(`/ai/jobs?${params.toString()}`);
  }

  cancelJob(jobId: string) {
    return this.request(`/ai/jobs/${jobId}/cancel`, { method: 'POST' });
  }

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

  getEDAJobStatus(jobId: string) {
    return this.request(`/eda/job/${jobId}`);
  }

  searchComponents(data: { q: string; category?: string; distributor?: string; limit?: number }) {
    return this.request('/components/search', { method: 'POST', body: JSON.stringify(data) });
  }

  getComponentCategories() {
    return this.request('/components/categories');
  }

  getFootprints(packageType: string) {
    return this.request(`/components/footprints/${packageType}`);
  }

  getComponentDetails(componentId: string) {
    return this.request(`/components/${componentId}`);
  }

  // Fabrication
  getQuotes(data: { design_id: string; options?: Record<string, unknown>; prefer_indian?: boolean }) {
    return this.request('/fab/quotes', { method: 'POST', body: JSON.stringify(data) });
  }

  listFabricators() {
    return this.request('/fab/fabricators');
  }

  // Analytics
  getDashboard(days = 30) {
    return this.request(`/analytics/dashboard?days=${days}`);
  }

  getDesignMetrics(designId: string) {
    return this.request(`/analytics/designs/${designId}/metrics`);
  }

  // Health
  healthCheck() {
    return this.request('/health');
  }

  readinessProbe() {
    return this.request('/health/ready');
  }

  deepHealthCheck() {
    return this.request('/health/deep');
  }
}

export const api = new ApiClient();
