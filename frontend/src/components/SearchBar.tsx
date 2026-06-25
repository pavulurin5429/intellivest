"use client";

import { useState } from "react";

interface Props {
  onSearch: (ticker: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [value, setValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim() || loading) return;
    onSearch(value.trim().toUpperCase());
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="relative flex items-center">
        <div className="absolute left-4 text-slate-500">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          placeholder="Enter ticker symbol — AAPL, MSFT, JPM, NVDA..."
          disabled={loading}
          className="w-full bg-slate-900/80 border border-slate-700/80 hover:border-slate-600 focus:border-blue-500/70 focus:ring-2 focus:ring-blue-500/20 rounded-xl pl-11 pr-36 py-3.5 text-white placeholder-slate-500 text-sm outline-none transition-all duration-200 mono disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="absolute right-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-all duration-200 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></span>
              Running
            </span>
          ) : "Analyze"}
        </button>
      </div>
    </form>
  );
}
