"use client";

import { useState } from "react";
import GalaxyMap from "../components/GalaxyMap";
import AudioPlayer from "../components/AudioPlayer";
import UploadModal from "../components/UploadModal";
import { Upload } from "lucide-react";

export default function Home() {
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  return (
    <main className="w-full h-screen relative overflow-hidden">
      {/* Top Navigation Overlay */}
      <div className="absolute top-0 left-0 right-0 z-20 flex justify-between items-center p-6 pointer-events-none">
        <h1 className="text-3xl font-black tracking-tighter mix-blend-difference text-white">STELLOS</h1>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="pointer-events-auto flex items-center space-x-2 bg-white/10 hover:bg-white/20 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 transition-all font-medium text-white"
        >
          <Upload size={18} />
          <span>Upload Track</span>
        </button>
      </div>

      {/* The Map */}
      <div className="absolute inset-0 z-0">
        <GalaxyMap />
      </div>

      {/* Upload Modal */}
      {isUploadOpen && (
        <UploadModal onClose={() => setIsUploadOpen(false)} />
      )}

      {/* Fixed bottom player */}
      <AudioPlayer />
    </main>
  );
}
