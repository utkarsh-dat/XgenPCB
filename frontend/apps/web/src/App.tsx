import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { Editor } from './pages/Editor';
import { SchematicEditor } from './pages/SchematicEditor';
import { Templates } from './pages/Templates';
import { Viewer3D } from './pages/Viewer3D';
import { DesignReview } from './pages/DesignReview';
import { Marketplace } from './pages/Marketplace';
import { Pricing } from './pages/Pricing';
import { Community } from './pages/Community';
import { Forum } from './pages/Forum';
import { TutorialView } from './pages/TutorialView';
import { UserProfile } from './pages/UserProfile';
import { AdminPanel } from './pages/AdminPanel';
import { LandingPage } from './pages/LandingPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/editor/:projectId/:designId" element={<Editor />} />
        <Route path="/schematic/:projectId/:designId" element={<SchematicEditor />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/viewer-3d/:designId" element={<Viewer3D />} />
        <Route path="/design-review/:designId" element={<DesignReview />} />
        <Route path="/marketplace" element={<Marketplace />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/community" element={<Community />} />
        <Route path="/forum" element={<Forum />} />
        <Route path="/tutorials" element={<TutorialView />} />
        <Route path="/profile" element={<UserProfile />} />
        <Route path="/admin" element={<AdminPanel />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
