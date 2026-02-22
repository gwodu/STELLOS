"use client";

import React, { useEffect, useState, useRef } from "react";
import DeckGL from "@deck.gl/react";
import { ScatterplotLayer, LineLayer } from "@deck.gl/layers";
import { useStore } from "../store";

export default function GalaxyMap() {
    const { tracks, setTracks, setHoveredTrack, hoveredTrack, setPlayingTrack, viewState, setViewState } = useStore();

    // A simple hacky audio ref to play previews instantly
    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        let alive = true;
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7860";

        const fetchTracks = async () => {
            try {
                const res = await fetch(`${apiUrl}/tracks?status=LIVE`);
                if (!res.ok) return;
                const data = await res.json();
                if (!alive) return;
                setTracks(data.tracks || []);
            } catch (e) {
                console.error("Failed to fetch tracks", e);
            }
        };

        fetchTracks();
        const id = setInterval(fetchTracks, 5000);
        return () => {
            alive = false;
            clearInterval(id);
        };
    }, [setTracks]);

    // Handle preview audio playback
    useEffect(() => {
        if (hoveredTrack && hoveredTrack.preview_file_url) {
            if (audioRef.current) {
                audioRef.current.src = hoveredTrack.preview_file_url;
                audioRef.current.play().catch(e => console.log('Autoplay blocked or aborted', e));
            }
        } else {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.currentTime = 0;
            }
        }
    }, [hoveredTrack]);

    const gravityLines = React.useMemo(() => {
        if (!tracks || tracks.length === 0) return [];
        const lines = [];
        // Connect each node to its 2 nearest neighbors to create a web
        for (let i = 0; i < tracks.length; i++) {
            const source = tracks[i];
            const neighbors = [...tracks]
                .filter(t => t.id !== source.id)
                .map(t => ({
                    target: t,
                    dist: Math.hypot(source.map_x - t.map_x, source.map_y - t.map_y)
                }))
                .sort((a, b) => a.dist - b.dist)
                .slice(0, 2);

            for (const n of neighbors) {
                // Ensure only one line per unique pair
                if (source.id < n.target.id) {
                    lines.push({
                        sourcePosition: [source.map_x, source.map_y],
                        targetPosition: [n.target.map_x, n.target.map_y]
                    });
                }
            }
        }
        return lines;
    }, [tracks]);

    const layers = [
        new LineLayer({
            id: 'gravity-lines',
            data: gravityLines,
            getSourcePosition: (d: any) => d.sourcePosition,
            getTargetPosition: (d: any) => d.targetPosition,
            getColor: [255, 255, 255, 60], // Truncated white for a subtle web effect
            getWidth: 1,
            widthMaxPixels: 2
        }),
        new ScatterplotLayer({
            id: "stars",
            data: tracks,
            pickable: true,
            opacity: 0.8,
            stroked: true,
            filled: true,
            radiusScale: 1,
            radiusMinPixels: 4,
            radiusMaxPixels: 30,
            lineWidthMinPixels: 1,
            getPosition: (d: any) => [d.map_x, d.map_y],
            getFillColor: (d: any) => (d.id === hoveredTrack?.id ? [255, 100, 100] : [100, 200, 255]),
            getLineColor: (d: any) => [255, 255, 255],
            getRadius: (d: any) => 4 + Math.min(20, d.vote_score || 0),
            onHover: ({ object }) => {
                if (object) {
                    setHoveredTrack(object);
                } else {
                    setHoveredTrack(null);
                }
            },
            onClick: ({ object }) => {
                if (object) {
                    setPlayingTrack(object);
                }
            }
        }),
    ];

    return (
        <div className="relative w-full h-screen bg-slate-900 overflow-hidden">
            {/* Invisible audio element for hover previews */}
            <audio ref={audioRef} />

            {/* We use an Orthographic view since it's just a 2D map for MVP */}
            <DeckGL
                initialViewState={{
                    ...viewState
                }}
                controller={true}
                layers={layers}
                onViewStateChange={({ viewState }) => setViewState(viewState)}
            >
                {/* We can inject custom HTML tooltips here later if needed */}
            </DeckGL>

            {hoveredTrack && (
                <div className="absolute top-4 left-4 bg-slate-800 text-white p-4 rounded shadow-lg border border-slate-700 pointer-events-none z-10 transition-opacity">
                    <p className="font-bold text-lg">{hoveredTrack.title}</p>
                    <p className="text-slate-400">{hoveredTrack.artist_name}</p>
                </div>
            )}
        </div>
    );
}
