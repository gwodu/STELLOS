import { create } from 'zustand';

// Assuming track structure matches DB
export interface Track {
    id: string;
    title: string;
    artist_name: string;
    audio_file_url: string;
    preview_file_url: string;
    status: string;
    map_x: number;
    map_y: number;
    vote_score?: number;
    licensing_enabled?: boolean;
    artist_id?: string;
}

interface StellosState {
    tracks: Track[];
    setTracks: (tracks: Track[]) => void;

    hoveredTrack: Track | null;
    setHoveredTrack: (track: Track | null) => void;

    playingTrack: Track | null;
    setPlayingTrack: (track: Track | null) => void;

    viewState: {
        longitude: number;
        latitude: number;
        zoom: number;
    };
    setViewState: (viewState: any) => void;
}

export const useStore = create<StellosState>((set) => ({
    tracks: [],
    setTracks: (tracks) => set({ tracks }),

    hoveredTrack: null,
    setHoveredTrack: (track) => set({ hoveredTrack: track }),

    playingTrack: null,
    setPlayingTrack: (track) => set({ playingTrack: track }),

    viewState: {
        longitude: 50, // Center of our 0-100 random map
        latitude: 50,
        zoom: 4,
    },
    setViewState: (viewState) => set({ viewState }),
}));
