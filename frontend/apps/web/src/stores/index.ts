/**
 * PCB Builder - Zustand State Stores
 */

import { create } from 'zustand';

// ── Types ────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string;
  visibility: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface BoardConfig {
  width_mm: number;
  height_mm: number;
  layers: number;
  thickness_mm: number;
  copper_weight: string;
  material: string;
  surface_finish: string;
}

export interface PlacedComponent {
  id: string;
  name: string;
  footprint: string;
  x: number;
  y: number;
  rotation: number;
  layer: string;
  value: string;
}

export interface Track {
  id: string;
  net: number;
  start: [number, number];
  end: [number, number];
  width: number;
  layer: string;
}

export interface Via {
  id: string;
  net: number;
  x: number;
  y: number;
  diameter: number;
  drill: number;
  from_layer: string;
  to_layer: string;
}

export interface Design {
  id: string;
  project_id: string;
  name: string;
  board_config: BoardConfig;
  schematic_data: Record<string, unknown>;
  pcb_layout: {
    placed_components: PlacedComponent[];
    tracks: Track[];
    vias: Via[];
  };
  constraints: Record<string, unknown>;
  version: number;
  status: string;
}

export interface DRCViolation {
  type: string;
  severity: 'error' | 'warning';
  message: string;
  location: { x: number; y: number };
}

export type EditorMode = 'schematic' | 'pcb' | '3d';
export type ToolMode = 'select' | 'place' | 'route' | 'measure' | 'zone';

// ── Design Store ─────────────────────────────────────────────

interface DesignState {
  currentDesign: Design | null;
  projects: Project[];
  isLoading: boolean;
  isSaving: boolean;
  drcViolations: DRCViolation[];
  setCurrentDesign: (design: Design | null) => void;
  setProjects: (projects: Project[]) => void;
  updateBoardConfig: (config: Partial<BoardConfig>) => void;
  addComponent: (component: PlacedComponent) => void;
  moveComponent: (id: string, x: number, y: number) => void;
  addTrack: (track: Track) => void;
  setDrcViolations: (violations: DRCViolation[]) => void;
  setLoading: (loading: boolean) => void;
  setSaving: (saving: boolean) => void;
}

export const useDesignStore = create<DesignState>((set) => ({
  currentDesign: null,
  projects: [],
  isLoading: false,
  isSaving: false,
  drcViolations: [],

  setCurrentDesign: (design) => set({ currentDesign: design }),
  setProjects: (projects) => set({ projects }),

  updateBoardConfig: (config) =>
    set((state) => ({
      currentDesign: state.currentDesign
        ? {
            ...state.currentDesign,
            board_config: { ...state.currentDesign.board_config, ...config },
          }
        : null,
    })),

  addComponent: (component) =>
    set((state) => {
      if (!state.currentDesign) return state;
      const layout = state.currentDesign.pcb_layout || { placed_components: [], tracks: [], vias: [] };
      return {
        currentDesign: {
          ...state.currentDesign,
          pcb_layout: {
            ...layout,
            placed_components: [...layout.placed_components, component],
          },
        },
      };
    }),

  moveComponent: (id, x, y) =>
    set((state) => {
      if (!state.currentDesign) return state;
      const layout = state.currentDesign.pcb_layout;
      return {
        currentDesign: {
          ...state.currentDesign,
          pcb_layout: {
            ...layout,
            placed_components: layout.placed_components.map((c) =>
              c.id === id ? { ...c, x, y } : c
            ),
          },
        },
      };
    }),

  addTrack: (track) =>
    set((state) => {
      if (!state.currentDesign) return state;
      const layout = state.currentDesign.pcb_layout;
      return {
        currentDesign: {
          ...state.currentDesign,
          pcb_layout: { ...layout, tracks: [...layout.tracks, track] },
        },
      };
    }),

  setDrcViolations: (violations) => set({ drcViolations: violations }),
  setLoading: (loading) => set({ isLoading: loading }),
  setSaving: (saving) => set({ isSaving: saving }),
}));

// ── UI Store ─────────────────────────────────────────────────

interface UIState {
  editorMode: EditorMode;
  toolMode: ToolMode;
  gridSize: number;
  snapToGrid: boolean;
  showChat: boolean;
  showProperties: boolean;
  showDRC: boolean;
  activeLayers: string[];
  zoom: number;
  panOffset: { x: number; y: number };
  selectedIds: string[];
  setEditorMode: (mode: EditorMode) => void;
  setToolMode: (mode: ToolMode) => void;
  setGridSize: (size: number) => void;
  toggleSnapToGrid: () => void;
  toggleChat: () => void;
  toggleProperties: () => void;
  toggleDRC: () => void;
  setZoom: (zoom: number) => void;
  setPanOffset: (offset: { x: number; y: number }) => void;
  setSelectedIds: (ids: string[]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  editorMode: 'pcb',
  toolMode: 'select',
  gridSize: 0.5,
  snapToGrid: true,
  showChat: true,
  showProperties: true,
  showDRC: false,
  activeLayers: ['F.Cu', 'B.Cu', 'F.SilkS', 'B.SilkS', 'Edge.Cuts'],
  zoom: 1,
  panOffset: { x: 0, y: 0 },
  selectedIds: [],

  setEditorMode: (mode) => set({ editorMode: mode }),
  setToolMode: (mode) => set({ toolMode: mode }),
  setGridSize: (size) => set({ gridSize: size }),
  toggleSnapToGrid: () => set((s) => ({ snapToGrid: !s.snapToGrid })),
  toggleChat: () => set((s) => ({ showChat: !s.showChat })),
  toggleProperties: () => set((s) => ({ showProperties: !s.showProperties })),
  toggleDRC: () => set((s) => ({ showDRC: !s.showDRC })),
  setZoom: (zoom) => set({ zoom }),
  setPanOffset: (offset) => set({ panOffset: offset }),
  setSelectedIds: (ids) => set({ selectedIds: ids }),
}));

// ── AI Store ─────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  actions?: Array<{ type: string; params: Record<string, unknown> }>;
  timestamp: number;
}

interface AIState {
  messages: ChatMessage[];
  isProcessing: boolean;
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setProcessing: (processing: boolean) => void;
  clearMessages: () => void;
}

export const useAIStore = create<AIState>((set) => ({
  messages: [
    {
      id: '1',
      role: 'assistant',
      content: "👋 Hi! I'm your PCB design assistant. I can help you with component placement, routing, DRC fixes, and design reviews. What would you like to do?",
      timestamp: Date.now(),
    },
  ],
  isProcessing: false,

  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...message, id: String(Date.now()), timestamp: Date.now() },
      ],
    })),

  setProcessing: (processing) => set({ isProcessing: processing }),
  clearMessages: () =>
    set({
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: "👋 Hi! I'm your PCB design assistant. How can I help?",
          timestamp: Date.now(),
        },
      ],
    }),
}));

// ── User Store ───────────────────────────────────────────────

interface UserState {
  user: { id: string; email: string; full_name: string; subscription_tier: string } | null;
  token: string | null;
  isAuthenticated: boolean;
  setUser: (user: UserState['user'], token: string) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  setUser: (user, token) => set({ user, token, isAuthenticated: true }),
  logout: () => set({ user: null, token: null, isAuthenticated: false }),
}));
