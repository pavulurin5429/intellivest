"use client";

import { useState } from "react";

const AGENTS = [
  { key: "fundamentals",  label: "Fundamentals",   icon: "📑", color: "blue" },
  { key: "technicals",    label: "Technicals",     icon: "📈", color: "violet" },
  { key: "sentiment",     label: "Sentiment",      icon: "💬", color: "amber" },
  { key: "risk_manager",  label: "Risk Manager",   icon: "🛡️", color: "rose" },
  { key: "fund_manager",  label: "Fund Manager",   icon: "⚖️", color: "emerald" },
];

const COLORS: Record<string, { border: string; bg: string; badge: string; dot: string }> = {
  blue:    { border: "border-blue-500/30",   bg: "bg-blue-500/5",   badge: "bg-blue-500/15 text-blue-300 border border-blue-500/20",   dot: "bg-blue-400" },
  violet:  { border: "border-violet-500/30", bg: "bg-violet-500/5", badge: "bg-violet-500/15 text-violet-300 border border-violet-500/20", dot: "bg-violet-400" },
  amber:   { border: "border-amber-500/30",  bg: "bg-amber-500/5",  badge: "bg-amber-500/15 text-amber-300 border border-amber-500/20",  dot: "bg-amber-400" },
  rose:    { border: "border-rose-500/30",   bg: "bg-rose-500/5",   badge: "bg-rose-500/15 text-rose-300 border border-rose-500/20",   dot: "bg-rose-400" },
  emerald: { border: "border-emerald-500/30",bg: "bg-emerald-500/5",badge: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/20",dot: "bg-emerald-400" },
};

const THESIS_STYLE: Record<string, string> = {
  BULLISH: "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20",
  NEUTRAL: "text-amber-400 bg-amber-500/10 border border-amber-500/20",
  BEARISH: "text-red-400 bg-red-500/10 border border-red-500/20",
  BUY:     "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20",
  HOLD:    "text-amber-400 bg-amber-500/10 border border-amber-500/20",
  SELL:    "text-red-400 bg-red-500/10 border border-red-500/20",
  LOW:     "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20",
  MEDIUM:  "text-amber-400 bg-amber-500/10 border border-amber-500/20",
  HIGH:    "text-orange-400 bg-orange-500/10 border border-orange-500/20",
  VERY_HIGH:"text-red-400 bg-red-500/10 border border-red-500/20",
};

function ConfidenceBar({ value, color }: { value: number; color: string }) {
  const TRACK_COLOR: Record<string, string> = {
    blue: "from-blue-600 to-blue-400",
    violet: "from-violet-600 to-violet-400",
    amber: "from-amber-600 to-amber-400",
    rose: "from-rose-600 to-rose-400",
    emerald: "from-emerald-600 to-emerald-400",
  };
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${TRACK_COLOR[color]} rounded-full transition-all duration-700`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-slate-500 text-xs mono w-8 text-right">{value}%</span>
    </div>
  );
}

export default function AgentDebateLog({ agentOutputs }: { agentOutputs: any }) {
  const [expanded, setExpanded] = useState<string | null>("fund_manager");
  if (!agentOutputs) return null;

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
        </svg>
        <h2 className="text-white text-sm font-semibold">Agent Debate Log</h2>
        <span className="ml-auto text-slate-600 text-xs">Click to expand</span>
      </div>

      <div className="divide-y divide-slate-800/50">
        {AGENTS.map(({ key, label, icon, color }) => {
          const agent = agentOutputs[key];
          if (!agent) return null;
          const isOpen = expanded === key;
          const stance = agent.thesis || agent.decision || agent.risk_rating || "N/A";
          const confidence = agent.confidence ?? null;
          const c = COLORS[color];

          return (
            <div key={key} className={`transition-colors ${isOpen ? c.bg : "hover:bg-slate-800/20"}`}>
              <button
                className="w-full flex items-center gap-3 px-5 py-3.5 text-left"
                onClick={() => setExpanded(isOpen ? null : key)}
              >
                <span className="text-base w-6 text-center">{icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-white text-sm font-medium">{label}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium mono ${THESIS_STYLE[stance] || "text-slate-400 bg-slate-800"}`}>
                      {stance}
                    </span>
                    {agent.error && (
                      <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">partial</span>
                    )}
                  </div>
                  {confidence !== null && !isOpen && (
                    <ConfidenceBar value={confidence} color={color} />
                  )}
                </div>
                <svg
                  className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isOpen && (
                <div className={`px-5 pb-4 border-t ${c.border}`}>
                  {confidence !== null && (
                    <div className="mt-3 mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-slate-500 text-xs">Confidence</span>
                      </div>
                      <ConfidenceBar value={confidence} color={color} />
                    </div>
                  )}

                  {agent.summary && (
                    <p className="text-slate-300 text-sm leading-relaxed mt-2 mb-3">{agent.summary}</p>
                  )}

                  {/* Fundamentals: factors */}
                  {key === "fundamentals" && (
                    <div className="space-y-2">
                      {agent.bullish_factors?.length > 0 && (
                        <div>
                          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Bullish factors</p>
                          <div className="flex flex-wrap gap-1.5">
                            {agent.bullish_factors.map((f: string, i: number) => (
                              <span key={i} className="text-xs px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {agent.risk_factors?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Risk factors</p>
                          <div className="flex flex-wrap gap-1.5">
                            {agent.risk_factors.map((f: string, i: number) => (
                              <span key={i} className="text-xs px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300">{f}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Technicals: key signals */}
                  {key === "technicals" && agent.key_signals?.length > 0 && (
                    <div>
                      <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Key signals</p>
                      <div className="flex flex-wrap gap-1.5">
                        {agent.key_signals.map((s: string, i: number) => (
                          <span key={i} className="text-xs px-2 py-1 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-300">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Risk Manager: position info */}
                  {key === "risk_manager" && (
                    <div className="flex flex-wrap gap-4 text-sm mt-1">
                      {agent.max_position_size && (
                        <div>
                          <span className="text-slate-500 text-xs block">Max position</span>
                          <span className="text-white font-semibold mono">{agent.max_position_size}</span>
                        </div>
                      )}
                      {agent.stop_loss_level && (
                        <div>
                          <span className="text-slate-500 text-xs block">Stop loss</span>
                          <span className="text-red-300 font-semibold mono">{agent.stop_loss_level}</span>
                        </div>
                      )}
                      {agent.key_risks?.length > 0 && (
                        <div className="w-full">
                          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1.5">Key risks</p>
                          <div className="flex flex-wrap gap-1.5">
                            {agent.key_risks.map((r: string, i: number) => (
                              <span key={i} className="text-xs px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300">{r}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Fund Manager: debate resolution */}
                  {key === "fund_manager" && (
                    <div className="space-y-3 mt-1">
                      {agent.target_weight && (
                        <div className="flex items-center gap-6">
                          <div>
                            <span className="text-slate-500 text-xs block">Target weight</span>
                            <span className="text-white font-bold text-lg mono">{agent.target_weight}</span>
                          </div>
                          {agent.price_target_90d && agent.price_target_90d !== "N/A" && (
                            <div>
                              <span className="text-slate-500 text-xs block">90D price target</span>
                              <span className="text-white font-semibold mono">{agent.price_target_90d}</span>
                            </div>
                          )}
                        </div>
                      )}
                      {agent.debate_resolution && (
                        <div className="bg-slate-800/50 rounded-lg px-3 py-2.5 border border-slate-700/50">
                          <p className="text-slate-500 text-xs uppercase tracking-wider mb-1">Debate resolution</p>
                          <p className="text-slate-300 text-sm italic">{agent.debate_resolution}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {agent.error && (
                    <p className="text-slate-500 text-xs mt-2 mono">{agent.error}</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
