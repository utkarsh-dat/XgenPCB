const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const isDev = !app.isPackaged || process.env.NODE_ENV === 'development';

let mainWindow;

// Directory to store offline PCB designs local to the user
const PROJECTS_DIR = path.join(app.getPath('userData'), 'local-projects');
if (!fs.existsSync(PROJECTS_DIR)) {
  fs.mkdirSync(PROJECTS_DIR, { recursive: true });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hidden', // Native looking title bar with traffic lights on macOS
    titleBarOverlay: process.platform === 'win32' ? {
      color: '#0f172a', // Slate 900
      symbolColor: '#f8fafc', // Slate 50
      height: 38
    } : false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    backgroundColor: '#0f172a', // Avoid white flash on load
    show: false
  });

  // Load target URL or local file
  if (isDev) {
    // Read port from env or default to 5173
    const port = process.env.PORT || 5173;
    mainWindow.loadURL(`http://localhost:${port}`);
    // Open DevTools in dev mode
    mainWindow.webContents.openDevTools();
  } else {
    // Look in potential build locations defensively
    const pathsToSearch = [
      path.join(__dirname, '../../web/dist/index.html'),
      path.join(__dirname, '../web/dist/index.html'),
      path.join(__dirname, 'web-dist/index.html')
    ];
    
    let loaded = false;
    for (const p of pathsToSearch) {
      if (fs.existsSync(p)) {
        mainWindow.loadFile(p);
        loaded = true;
        break;
      }
    }
    if (!loaded) {
      console.error('Could not find packaged index.html in paths:', pathsToSearch);
      // Fallback
      mainWindow.loadFile(path.join(__dirname, '../../web/dist/index.html')).catch(err => {
        console.error('Failed to load fallback index.html:', err);
      });
    }
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open external links in user default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  // Register IPC handlers
  setupIPCHandlers();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

function setupIPCHandlers() {
  // Native dialogs
  ipcMain.handle('dialog:open-file', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      ...options
    });
    if (!result.canceled && result.filePaths.length > 0) {
      const filePath = result.filePaths[0];
      const content = fs.readFileSync(filePath, 'utf-8');
      return { filePath, content };
    }
    return null;
  });

  ipcMain.handle('dialog:save-file', async (event, { content, options }) => {
    const result = await dialog.showSaveDialog(mainWindow, options);
    if (!result.canceled && result.filePath) {
      fs.writeFileSync(result.filePath, content, 'utf-8');
      return result.filePath;
    }
    return null;
  });

  // Local Project storage (off-line desktop capabilities)
  ipcMain.handle('projects:list', async () => {
    try {
      const files = fs.readdirSync(PROJECTS_DIR);
      const projects = [];
      for (const file of files) {
        if (file.endsWith('.json')) {
          const filePath = path.join(PROJECTS_DIR, file);
          const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
          projects.push({
            id: file.replace('.json', ''),
            name: data.name || 'Untitled Project',
            updatedAt: data.updatedAt || fs.statSync(filePath).mtime.toISOString(),
            description: data.description || '',
            boardConfig: data.boardConfig || null
          });
        }
      }
      return projects.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    } catch (err) {
      console.error('Error listing local projects:', err);
      return [];
    }
  });

  ipcMain.handle('projects:get', async (event, projectId) => {
    try {
      const filePath = path.join(PROJECTS_DIR, `${projectId}.json`);
      if (fs.existsSync(filePath)) {
        return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      }
      return null;
    } catch (err) {
      console.error(`Error getting project ${projectId}:`, err);
      return null;
    }
  });

  ipcMain.handle('projects:save', async (event, { projectId, data }) => {
    try {
      const filePath = path.join(PROJECTS_DIR, `${projectId}.json`);
      const payload = {
        ...data,
        updatedAt: new Date().toISOString()
      };
      fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), 'utf-8');
      return true;
    } catch (err) {
      console.error(`Error saving project ${projectId}:`, err);
      return false;
    }
  });

  ipcMain.handle('projects:delete', async (event, projectId) => {
    try {
      const filePath = path.join(PROJECTS_DIR, `${projectId}.json`);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
        return true;
      }
      return false;
    } catch (err) {
      console.error(`Error deleting project ${projectId}:`, err);
      return false;
    }
  });

  // Window Controls (for custom title bars)
  ipcMain.on('window:minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('window:maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.restore();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.on('window:close', () => {
    if (mainWindow) mainWindow.close();
  });

  ipcMain.handle('window:is-maximized', () => {
    return mainWindow ? mainWindow.isMaximized() : false;
  });
}
