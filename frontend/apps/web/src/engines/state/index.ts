// State Engine: Manages application state, reactive stores, and real-time updates
import { create } from 'zustand';

export interface AppState {
  isDarkMode: boolean;
  activeTool: string;
  toggleTheme: () => void;
  setActiveTool: (tool: string) => void;
}

export const useStateEngine = create<AppState>((set) => ({
  isDarkMode: true,
  activeTool: 'select',
  toggleTheme: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  setActiveTool: (tool) => set({ activeTool: tool }),
}));
