import { useRef } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Grid } from '@react-three/drei';
import { useNavigate, useParams } from 'react-router-dom';

interface PCBBoardProps {
  layers: number;
  width: number;
  height: number;
}

function PCBBoard({ layers, width, height }: PCBBoardProps) {
  const boardRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (boardRef.current) {
      boardRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
  });

  return (
    <group ref={boardRef}>
      <mesh position={[0, layers * 0.8, 0]}>
        <boxGeometry args={[width, layers * 1.6, height]} />
        <meshStandardMaterial 
          color="#1a5f2a" 
          transparent 
          opacity={0.85}
          roughness={0.3}
          metalness={0.1}
        />
      </mesh>
      
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[width, 0.1, height]} />
        <meshStandardMaterial color="#b87333" metalness={0.9} roughness={0.2} />
      </mesh>
      
      {layers >= 2 && (
        <mesh position={[0, 0.8, 0]}>
          <boxGeometry args={[width, 0.1, height]} />
          <meshStandardMaterial color="#b87333" metalness={0.9} roughness={0.2} />
        </mesh>
      )}

      {[...Array(8)].map((_, i) => (
        <mesh key={i} position={[
          (Math.random() - 0.5) * width * 0.8,
          0.2,
          (Math.random() - 0.5) * height * 0.8
        ]}>
          <boxGeometry args={[2, 1, 1.5]} />
          <meshStandardMaterial color="#222" roughness={0.5} metalness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

function Components() {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[6, 4, 3]} />
        <meshStandardMaterial color="#1a1a2e" roughness={0.4} />
      </mesh>
      
      <mesh position={[8, 2, 5]}>
        <cylinderGeometry args={[2, 2, 4, 16]} />
        <meshStandardMaterial color="#222" metalness={0.6} />
      </mesh>
    </group>
  );
}

export function Viewer3D() {
  const navigate = useNavigate();
  const { projectId, designId } = useParams();

  return (
    <div className="app-layout">
      <nav className="topnav">
        <div className="topnav__logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <div className="topnav__logo-icon">⚡</div>
          PCB Builder
        </div>
        
        <div className="topnav__tabs">
          <button 
            className="topnav__tab" 
            onClick={() => navigate(`/editor/${projectId || 'new'}/${designId || 'design-1'}`)}
          >
            📋 Editor
          </button>
          <button className="topnav__tab topnav__tab--active">📦 3D Viewer</button>
        </div>

        <div className="topnav__actions">
          <button className="btn btn--primary btn--sm btn--glow">
            📸 Export Image
          </button>
        </div>
      </nav>

      <div className="viewer-3d">
        <Canvas shadows>
          <PerspectiveCamera makeDefault position={[40, 30, 40]} fov={50} />
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            autoRotate
            autoRotateSpeed={0.5}
            minDistance={20}
            maxDistance={100}
          />
          
          <ambientLight intensity={0.4} />
          <directionalLight 
            position={[20, 30, 20]} 
            intensity={1.2} 
            castShadow
            shadow-mapSize={[2048, 2048]}
          />
          <pointLight position={[-10, 10, -10]} intensity={0.5} color="#8b5cf6" />
          
          <Environment preset="city" />
          
          <PCBBoard layers={2} width={32} height={18} />
          <Components />
          
          <Grid 
            position={[0, -0.1, 0]} 
            args={[100, 100]} 
            cellSize={5} 
            cellThickness={0.5}
            cellColor="#3f3f46"
            sectionSize={20}
            sectionThickness={1}
            sectionColor="#8b5cf6"
            fadeDistance={50}
            fadeStrength={1}
          />
        </Canvas>

        <div className="viewer-3d__controls">
          <button className="viewer-3d__btn" title="Rotate">↻</button>
          <button className="viewer-3d__btn" title="Zoom In">+</button>
          <button className="viewer-3d__btn" title="Zoom Out">−</button>
          <button className="viewer-3d__btn" title="Reset">⊡</button>
          <button className="viewer-3d__btn viewer-3d__btn--active" title="Auto Rotate">◉</button>
        </div>

        <div className="viewer-3d__info">
          <div className="viewer-3d__info-row">
            <span className="viewer-3d__info-label">Layers</span>
            <span className="viewer-3d__info-value">2</span>
          </div>
          <div className="viewer-3d__info-row">
            <span className="viewer-3d__info-label">Size</span>
            <span className="viewer-3d__info-value">80 x 50 mm</span>
          </div>
          <div className="viewer-3d__info-row">
            <span className="viewer-3d__info-label">Components</span>
            <span className="viewer-3d__info-value">24</span>
          </div>
          <div className="viewer-3d__info-row">
            <span className="viewer-3d__info-label">Traces</span>
            <span className="viewer-3d__info-value">156</span>
          </div>
        </div>
      </div>

      <div className="statusbar">
        <div className="statusbar__item"><span className="statusbar__dot" /> Connected</div>
        <div className="statusbar__item" style={{ marginLeft: 'auto' }}>
          Press <kbd>R</kbd> Rotate &nbsp; <kbd>Scroll</kbd> Zoom &nbsp; <kbd>Space</kbd> Auto Rotate
        </div>
      </div>
    </div>
  );
}