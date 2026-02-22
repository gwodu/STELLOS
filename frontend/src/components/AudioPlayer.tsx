"use client";

import React, { useRef, useEffect, useState } from "react";
import { useStore } from "../store";
import { Play, Pause, SkipForward, Volume2 } from "lucide-react";

export default function AudioPlayer() {
    const { playingTrack, setPlayingTrack, tracks, setTracks } = useStore();
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [balance, setBalance] = useState<number | null>(null);
    const [voteLoading, setVoteLoading] = useState(false);
    const [templates, setTemplates] = useState<any[]>([]);
    const [licenseLoading, setLicenseLoading] = useState(false);
    const [licenseMessage, setLicenseMessage] = useState<string | null>(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7860";

    useEffect(() => {
        const existing = typeof window !== "undefined" ? localStorage.getItem("stellos_session_id") : null;
        if (existing) {
            setSessionId(existing);
            return;
        }
        const newId = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `sess_${Date.now()}`;
        if (typeof window !== "undefined") {
            localStorage.setItem("stellos_session_id", newId);
        }
        setSessionId(newId);
    }, []);

    useEffect(() => {
        if (!sessionId) return;
        const fetchBalance = async () => {
            try {
                const res = await fetch(`${apiUrl}/tokens/balance?session_id=${sessionId}`);
                if (!res.ok) return;
                const data = await res.json();
                setBalance(data.balance);
            } catch (e) {
                console.error("Failed to load token balance", e);
            }
        };
        fetchBalance();
    }, [sessionId, apiUrl]);

    useEffect(() => {
        if (!playingTrack) {
            setTemplates([]);
            setLicenseMessage(null);
            return;
        }
        const fetchTemplates = async () => {
            try {
                const res = await fetch(`${apiUrl}/tracks/${playingTrack.id}/license-templates`);
                if (!res.ok) return;
                const data = await res.json();
                setTemplates(data.templates || []);
            } catch (e) {
                console.error("Failed to load license templates", e);
            }
        };
        fetchTemplates();
    }, [playingTrack, apiUrl]);

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

    const handleVote = async () => {
        if (!playingTrack || !sessionId || voteLoading) return;
        setVoteLoading(true);
        try {
            const res = await fetch(`${apiUrl}/tracks/${playingTrack.id}/vote`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, tokens_spent: 1 })
            });
            const data = await res.json();
            if (res.ok) {
                setBalance(data.balance);
                const updated = tracks.map(t => t.id === playingTrack.id ? { ...t, vote_score: data.vote_score } : t);
                setTracks(updated);
                setPlayingTrack({ ...playingTrack, vote_score: data.vote_score });
            } else {
                alert(data.detail || "Vote failed");
            }
        } catch (e) {
            console.error(e);
        } finally {
            setVoteLoading(false);
        }
    };

    const handleLicense = async (templateId: string) => {
        if (!playingTrack || licenseLoading) return;
        setLicenseLoading(true);
        setLicenseMessage(null);
        try {
            const res = await fetch(`${apiUrl}/tracks/${playingTrack.id}/license`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ license_template_id: templateId })
            });
            const data = await res.json();
            if (res.ok) {
                setLicenseMessage(`License purchased. Hash: ${data.license_hash}`);
            } else {
                setLicenseMessage(data.detail || "License failed");
            }
        } catch (e) {
            console.error(e);
            setLicenseMessage("License failed");
        } finally {
            setLicenseLoading(false);
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

            {/* Right Actions */}
            <div className="flex-1 flex flex-col items-end space-y-2">
                <div className="flex items-center space-x-3">
                    <span className="text-xs text-slate-400">Tokens: {balance ?? "..."}</span>
                    <button
                        onClick={handleVote}
                        disabled={voteLoading || balance === 0}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-xs font-semibold transition-colors"
                    >
                        {voteLoading ? "Voting..." : "Upvote (1)"}
                    </button>
                </div>
                <div className="flex items-center space-x-2">
                    {templates.length > 0 ? (
                        <>
                            <span className="text-xs text-slate-400">${(templates[0].price_cents / 100).toFixed(2)}</span>
                            <button
                                onClick={() => handleLicense(templates[0].id)}
                                disabled={licenseLoading}
                                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-full text-xs font-semibold transition-colors"
                            >
                                {licenseLoading ? "Licensing..." : "License Now"}
                            </button>
                        </>
                    ) : (
                        <span className="text-xs text-slate-500">No license</span>
                    )}
                </div>
                {licenseMessage && (
                    <div className="text-[10px] text-slate-400 max-w-xs text-right">{licenseMessage}</div>
                )}
            </div>
        </div>
    );
}
