"use client";

import React, { useState } from "react";
import { UploadCloud } from "lucide-react";
import { useStore } from "../store";

export default function UploadModal({ onClose }: { onClose: () => void }) {
    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState("");
    const [artist, setArtist] = useState("");
    const [uploading, setUploading] = useState(false);
    const { tracks, setTracks } = useStore();

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setUploading(true);
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", title || file.name);
        formData.append("artist_name", artist || "Unknown Artist");

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7860";
            const res = await fetch(`${apiUrl}/upload`, {
                method: "POST",
                body: formData,
            });

            if (res.ok) {
                // Technically we should poll or push to state, but for MVP we will just close.
                // The track gets placed randomly almost immediately since preview/embedding are async.
                onClose();
                alert("Upload started! The track will appear on the map shortly.");
            } else {
                alert("Upload failed.");
            }
        } catch (err) {
            console.error(err);
            alert("Upload error.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl border border-slate-700">
                <h2 className="text-2xl font-bold text-white mb-6">Upload Track</h2>

                <form onSubmit={handleUpload} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">Audio File</label>
                        <div className="border-2 border-dashed border-slate-600 rounded-lg p-6 flex flex-col items-center justify-center hover:bg-slate-700/50 transition-colors cursor-pointer relative">
                            <input
                                type="file"
                                accept="audio/*"
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                onChange={(e) => setFile(e.target.files?.[0] || null)}
                                required
                            />
                            <UploadCloud className="text-slate-400 mb-2" size={32} />
                            <span className="text-sm text-slate-400">
                                {file ? file.name : "Click or drag audio file here"}
                            </span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">Title</label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                            placeholder="Track Title"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">Artist</label>
                        <input
                            type="text"
                            value={artist}
                            onChange={(e) => setArtist(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                            placeholder="Artist Name"
                        />
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!file || uploading}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                        >
                            {uploading ? "Uploading..." : "Upload"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
