"use client";

import React, { useState } from "react";
import { useStore } from "../store";
import { Radio, Send } from "lucide-react";

export default function RadioPanel() {
    const [prompt, setPrompt] = useState("");
    const { playingTrack, setPlayingTrack } = useStore();
    const [isRadioActive, setIsRadioActive] = useState(false);

    const handleStartRadio = () => {
        setIsRadioActive(true);
        // MVP logic: just start playing something if nothing is playing
        // and rely on POST /radio/next for the queue
        if (!playingTrack) {
            // Simple fallback
            alert("Select a track first or wait for the map to load!");
        } else {
            alert("Radio mode activated! Trajectory line will appear.");
        }
    };

    const handleSteer = (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        // In a real MVP, this hits POST /radio/next with the prompt
        // to search vector space for `audio_emb + text_emb`
        console.log("Steering radio towards:", prompt);
        alert(`Steering radio towards: "${prompt}" (Hitting POST /radio/next constraint)`);
        setPrompt("");
    };

    return (
        <div className="absolute top-24 right-6 w-80 bg-slate-800/90 backdrop-blur-md border border-slate-700 rounded-2xl shadow-2xl p-5 text-white z-10 transition-all">
            <div className="flex items-center space-x-3 mb-4">
                <div className={`p-2 rounded-full ${isRadioActive ? 'bg-blue-500 animate-pulse' : 'bg-slate-700'}`}>
                    <Radio size={20} />
                </div>
                <h2 className="text-xl font-bold tracking-tight">Live Radio</h2>
            </div>

            {!isRadioActive ? (
                <div className="text-center py-6">
                    <p className="text-slate-400 text-sm mb-4">Start wandering the galaxy map automatically based on audio similarity.</p>
                    <button
                        onClick={handleStartRadio}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 rounded-lg transition-colors"
                    >
                        Start Autoplay
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="p-3 bg-slate-900 rounded-lg text-sm text-slate-300">
                        <p className="font-semibold text-blue-400 mb-1">Current Trajectory:</p>
                        <p>Drifting through nearest neighbors</p>
                    </div>

                    <form onSubmit={handleSteer} className="relative mt-2">
                        <input
                            type="text"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="e.g. darker, faster, less vocals..."
                            className="w-full bg-slate-900 border border-slate-600 rounded-full px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors pr-10"
                        />
                        <button
                            type="submit"
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-blue-400 transition-colors"
                        >
                            <Send size={16} />
                        </button>
                    </form>
                    <div className="text-xs text-slate-500 text-center mt-2">
                        AI applies natural language steering directly to the audio vector space.
                    </div>
                </div>
            )}
        </div>
    );
}
