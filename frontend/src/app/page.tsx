"use client";

import { useState, useEffect, useRef } from "react";
import { triggerAnalysis, getAnalysisStatus, downloadReport } from "../lib/api";
import { createWebSocket } from "../lib/websocket";
import AgentDebateLog from "../components/AgentDebateLog";
import DecisionBanner from "../components/DecisionBanner";
import RiskMetrics from "../components/RiskMetrics";
import Navbar from "../components/Navbar";
import SearchBar from "../components/SearchBar";
import AnalysisLoader from "../components/AnalysisLoader";

export default function Dashboard() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const pendingSubscribeRef = useRef<string | null>(null);

  // Create WS once on mount; handle pending subscriptions via onopen
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws");
    wsRef.current = ws;

    ws.onopen = () => {
      if (pendingSubscribeRef.current) {
        ws.send(JSON.stringify({ subscribe: pendingSubscribeRef.current }));
        pendingSubscribeRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "update") {
          setResult((prev: any) => {
            if (!prev?.ticker) return prev;
            const update = data.data?.[prev.ticker];
            if (update?.status === "complete") {
              setLoading(false);
              if (pollRef.current) clearInterval(pollRef.current);
              return update;
            }
            return prev;
          });
        }
      } catch (e) {
        console.error("WebSocket parse error:", e);
      }
    };

    ws.onerror = () => console.error("WebSocket connection failed");
    ws.onclose = () => {
      // Reconnect after 3s if closed unexpectedly
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          wsRef.current = null;
        }
      }, 3000);
    };

    return () => ws.close();
  }, []);

  async function handleAnalyze(t: string) {
    const sym = t.trim().toUpperCase();
    if (!sym) return;
    setTicker(sym);
    setLoading(true);
    setError("");
    setResult({ ticker: sym, status: "running" });

    try {
      await triggerAnalysis(sym);
      // Subscribe via WS — queue if not yet open
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ subscribe: sym }));
      } else {
        pendingSubscribeRef.current = sym;
      }
      pollRef.current = setInterval(async () => {
        const status = await getAnalysisStatus(sym);
        if (status?.status === "complete") {
          setResult(status);
          setLoading(false);
          clearInterval(pollRef.current!);
        } else if (status?.status === "error") {
          setError(status.error || "Analysis failed");
          setLoading(false);
          clearInterval(pollRef.current!);
        }
      }, 3000);
    } catch {
      setError("Cannot reach backend. Make sure it is running on port 8000.");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#080c14]">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {/* Hero search */}
        <div className={`transition-all duration-500 ${result ? "mb-8" : "mb-16 mt-12"}`}>
          {!result && (
            <div className="text-center mb-8 animate-slide-up">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium mb-4">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse-slow"></span>
                5-Agent LLM Analysis Engine Active
              </div>
              <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
                Investment Intelligence Platform
              </h1>
              <p className="text-slate-400 text-lg max-w-xl mx-auto">
                Enter any ticker to trigger a full multi-agent analysis — fundamentals, technicals, sentiment, risk, and a final investment decision.
              </p>
            </div>
          )}
          <SearchBar onSearch={handleAnalyze} loading={loading} />
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 bg-red-500/8 border border-red-500/25 rounded-xl p-4 mb-6 animate-slide-up">
            <svg className="w-5 h-5 text-red-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && <AnalysisLoader ticker={ticker} />}

        {/* Results */}
        {result?.status === "complete" && (
          <div className="space-y-5 animate-slide-up">
            <DecisionBanner result={result} onDownload={() => downloadReport(result.ticker)} />
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
              <div className="xl:col-span-2">
                <AgentDebateLog agentOutputs={result.agent_outputs} />
              </div>
              <div>
                <RiskMetrics riskOutput={result.agent_outputs?.risk_manager} />
              </div>
            </div>
            {result.errors?.length > 0 && (
              <div className="bg-amber-500/8 border border-amber-500/20 rounded-xl p-4">
                <p className="text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">Warnings</p>
                {result.errors.map((e: string, i: number) => (
                  <p key={i} className="text-amber-300/70 text-xs mono">{e}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!loading && !result && !error && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 animate-slide-up">
            {[
              { ticker: "AAPL", label: "Apple Inc.", badge: "Large Cap" },
              { ticker: "JPM", label: "JPMorgan Chase", badge: "Financials" },
              { ticker: "NVDA", label: "NVIDIA Corp.", badge: "Semiconductors" },
            ].map((s) => (
              <button
                key={s.ticker}
                onClick={() => handleAnalyze(s.ticker)}
                className="group flex items-center justify-between p-4 bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-600 rounded-xl transition-all duration-200"
              >
                <div className="text-left">
                  <div className="text-white font-semibold mono">{s.ticker}</div>
                  <div className="text-slate-500 text-sm">{s.label}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">{s.badge}</span>
                  <svg className="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-4 px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-600">
          <span>IntelliVest · SFDR Article 8 · Not financial advice</span>
          <span className="mono">v1.0.0</span>
        </div>
      </footer>
    </div>
  );
}
