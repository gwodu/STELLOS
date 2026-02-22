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
        // Local Demo Mock Data for Visuals (Mainstream vs SoundCloud/Indie)
        const mockTracks = [
            // MAINSTREAM CLUSTER
            { id: "1", title: "Not Like Us", artist_name: "Kendrick Lamar", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 60, map_y: 60 },
            { id: "2", title: "God's Plan", artist_name: "Drake", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 62, map_y: 58 },
            { id: "3", title: "The Hills", artist_name: "The Weeknd", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 58, map_y: 65 },
            { id: "4", title: "Cruel Summer", artist_name: "Taylor Swift", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 50, map_y: 55 },
            { id: "5", title: "Bad Guy", artist_name: "Billie Eilish", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 48, map_y: 60 },
            { id: "6", title: "Blinding Lights", artist_name: "The Weeknd", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 55, map_y: 62 },
            { id: "7", title: "As It Was", artist_name: "Harry Styles", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 45, map_y: 52 },

            // SOUNDCLOUD / INDIE / BEGINNER CLUSTER
            { id: "8", title: "chillhop study loop 4", artist_name: "lofi_beats_247", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 20, map_y: 20 },
            { id: "9", title: "first track on fl studio be nice", artist_name: "new_producer99", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 15, map_y: 80 },
            { id: "10", title: "dark trap type beat", artist_name: "prod. shadow", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 80, map_y: 20 },
            { id: "11", title: "bedroom pop guitar draft", artist_name: "sad_boy_summer", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 10, map_y: 35 },
            { id: "12", title: "mumble rap freestyle pt 2", artist_name: "yung starz", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 85, map_y: 15 },
            { id: "13", title: "hyperpop glitchcore test mix", artist_name: "xX_starlight.zip_Xx", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 90, map_y: 90 },
            { id: "14", title: "ambient drone (unfinished)", artist_name: "echoes_in_space", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 5, map_y: 10 },
            { id: "15", title: "my sister singing", artist_name: "local_band_drafts", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 35, map_y: 85 },
            { id: "16", title: "Vaporwave Mall 1995", artist_name: "Macintosh Plus Fan", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 25, map_y: 30 },
            { id: "17", title: "EDM Festival Banger WIP v8", artist_name: "DJ Spark Drop", audio_file_url: "", preview_file_url: "", status: "LIVE", map_x: 75, map_y: 75 },
        ];
        setTracks(mockTracks as any[]);
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
            radiusMaxPixels: 20,
            lineWidthMinPixels: 1,
            getPosition: (d: any) => [d.map_x, d.map_y],
            getFillColor: (d: any) => (d.id === hoveredTrack?.id ? [255, 100, 100] : [100, 200, 255]),
            getLineColor: (d: any) => [255, 255, 255],
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
