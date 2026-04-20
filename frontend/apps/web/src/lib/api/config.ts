/**
 * PCB Builder - API Configuration
 */

export const API_CONFIG = {
  baseUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000',
  timeout: 30000,
};

export const getApiUrl = (endpoint: string) => `${API_CONFIG.baseUrl}${endpoint}`;