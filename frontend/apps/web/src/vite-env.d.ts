/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_WS_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  electronAPI?: {
    isElectron: boolean;
    openFile(options?: any): Promise<{ filePath: string; content: string } | null>;
    saveFile(content: string, options?: any): Promise<string | null>;
    listProjects(): Promise<any[]>;
    getProject(projectId: string): Promise<any | null>;
    saveProject(projectId: string, data: any): Promise<boolean>;
    deleteProject(projectId: string): Promise<boolean>;
    minimizeWindow(): void;
    maximizeWindow(): void;
    closeWindow(): void;
    isMaximized(): Promise<boolean>;
  };
}