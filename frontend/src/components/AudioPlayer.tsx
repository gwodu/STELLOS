"use client";

import React, { useRef, useEffect, useState } from "react";
import { useStore } from "../store";
import { Play, Pause, SkipForward, Volume2 } from "lucide-react";

export default function AudioPlayer() {
    const { playingTrack, setPlayingTrack } = useStore();
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        if (playingTrack && audioRef.current) {
            audioRef.current.src = playingTrack.audio_file_url;
            audioRef.current.play().then(() => setIsPlaying(true)).catch(e => console.error(e));
        }
    }, [playingTrack]);

    const togglePlay = () => {
        if (!audioRef.current) return;
        if (isPlaying) {
            audioRef.current.pause();
        } else {
            audioRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            const p = (audioRef.current.currentTime / audioRef.current.duration) * 100;
            setProgress(isNaN(p) ? 0 : p);
        }
    };

    if (!playingTrack) return null;

    return (
        <div className="fixed bottom-0 left-0 right-0 h-24 bg-slate-900 border-t border-slate-800 text-white flex items-center px-6 z-50">
            <audio ref={audioRef} onTimeUpdate={handleTimeUpdate} onEnded={() => setIsPlaying(false)} />

            {/* Track Info */}
            <div className="flex-1 flex flex-col">
                <h3 className="font-bold text-lg leading-tight">{playingTrack.title}</h3>
                <p className="text-slate-400 text-sm">{playingTrack.artist_name}</p>
            </div>

            {/* Controls */}
            <div className="flex-1 flex flex-col items-center justify-center space-y-2">
                <div className="flex items-center space-x-6">
                    <button className="text-slate-400 hover:text-white transition-colors">
                        <Volume2 size={20} />
                    </button>
                    <button
                        onClick={togglePlay}
                        className="w-12 h-12 flex items-center justify-center bg-white text-slate-900 rounded-full hover:scale-105 transition-transform"
                    >
                        {isPlaying ? <Pause fill="currentColor" size={24} /> : <Play fill="currentColor" size={24} />}
                    </button>
                    <button className="text-slate-400 hover:text-white transition-colors">
                        <SkipForward size={20} />
                    </button>
                </div>

                {/* Progress Bar */}
                <div className="w-full max-w-md h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 transition-all duration-100 ease-linear" style={{ width: `${progress}%` }} />
                </div>
            </div>

            {/* Right Spacer for balance */}
            <div className="flex-1 flex justify-end">
                <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-full text-sm font-semibold transition-colors">
                    Start Radio
                </button>
            </div>
        </div>
    );
}
