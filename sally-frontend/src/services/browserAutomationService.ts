import api from './authService';

export interface BrowserTaskRequest {
  task: string;
  url?: string;
  model_name?: string;
  max_steps?: number;
  cdp_url?: string;
  use_current_page?: boolean;
}

export interface BrowserTaskResponse {
  success: boolean;
  result?: string;
  error?: string;
  execution_time: number;
  metadata: {
    task?: string;
    url?: string;
    steps?: number;
    max_steps?: number;
    model_used?: string;
  };
}

export interface BrowserHealthResponse {
  status: string;
  browser_initialized: boolean;
  llm_initialized: boolean;
  openrouter_configured: boolean;
}

export interface AvailableModel {
  name: string;
  provider: string;
  type: string;
  streaming: boolean;
  max_context_length: number;
}

class BrowserAutomationService {
  /**
   * اجرای یک وظیفه browser automation
   */
  async executeTask(request: BrowserTaskRequest): Promise<BrowserTaskResponse> {
    try {
      const response = await api.post<BrowserTaskResponse>(
        '/api/browser/execute',
        request
      );
      return response.data;
    } catch (error: any) {
      console.error('Browser automation request failed:', error);
      throw error;
    }
  }

  /**
   * اجرای غیرهمزمان یک وظیفه (برای وظایف طولانی)
   */
  async executeTaskAsync(request: BrowserTaskRequest): Promise<{ status: string; message: string; task: string }> {
    try {
      const response = await api.post(
        '/api/browser/execute-async',
        request
      );
      return response.data;
    } catch (error: any) {
      console.error('Async browser automation request failed:', error);
      throw error;
    }
  }

  /**
   * بررسی وضعیت سلامت سرویس browser automation
   */
  async getHealth(): Promise<BrowserHealthResponse> {
    try {
      const response = await api.get<BrowserHealthResponse>('/api/browser/health');
      return response.data;
    } catch (error: any) {
      console.error('Browser health check failed:', error);
      throw error;
    }
  }

  /**
   * دریافت لیست مدل‌های موجود برای browser automation
   */
  async getAvailableModels(): Promise<AvailableModel[]> {
    try {
      const response = await api.get<{ models: AvailableModel[] }>('/api/browser/available-models');
      return response.data.models || [];
    } catch (error: any) {
      console.error('Failed to get available models:', error);
      throw error;
    }
  }

  /**
   * اجرای دستور agent برای تعامل با پنل ادمین
   * این متد برای دستورات پیچیده‌تر مانند ساخت کاربر، مدیریت مقالات و غیره استفاده می‌شود
   */
  async executeAgentCommand(request: BrowserTaskRequest): Promise<BrowserTaskResponse> {
    try {
      const response = await api.post<BrowserTaskResponse>(
        '/api/browser/agent-execute',
        request
      );
      return response.data;
    } catch (error: any) {
      console.error('Agent command execution failed:', error);
      throw error;
    }
  }
}

export const browserAutomationService = new BrowserAutomationService();

