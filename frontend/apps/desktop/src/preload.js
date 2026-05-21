const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  
  // File Dialogs
  openFile: (options) => ipcRenderer.invoke('dialog:open-file', options),
  saveFile: (content, options) => ipcRenderer.invoke('dialog:save-file', { content, options }),
  
  // Local Project Store
  listProjects: () => ipcRenderer.invoke('projects:list'),
  getProject: (projectId) => ipcRenderer.invoke('projects:get', projectId),
  saveProject: (projectId, data) => ipcRenderer.invoke('projects:save', { projectId, data }),
  deleteProject: (projectId) => ipcRenderer.invoke('projects:delete', projectId),
  
  // Window controls
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:is-maximized')
});
