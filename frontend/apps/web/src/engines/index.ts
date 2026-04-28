// Frontend Architecture: 6 Core Engines
// This serves as the central API for the entire PCB Builder Application.

export * from './ui';
export * from './canvas';
export * from './state';
export * from './command';
export * from './file';
export * from './ai';

// Application Coordinator
export class EngineCoordinator {
  initialize() {
    console.log('Initializing PCB Builder Core Architecture...');
    // Initialize order is critical
    
    // 1. State Engine is already active (Zustand)
    
    // 2. Setup Command Engine Keybindings
    import('./command').then(({ commandEngine }) => {
      commandEngine.registerKeybindings();
    });
    
    // 3. Canvas Engine connects to DOM later via React Component
    
    // 4. Connect AI interaction logic
    // ...
  }
}

export const coreApp = new EngineCoordinator();
