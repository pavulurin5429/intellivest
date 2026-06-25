"use client";

const DECISION_STYLES: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  BUY:  { bg: "bg-emerald-500/8",  border: "border-emerald-500/30", text: "text-emerald-400", badge: "bg-emerald-500/15 text-emerald-300" },
  HOLD: { bg: "bg-amber-500/8",    border: "border-amber-500/30",   text: "text-amber-400",   badge: "bg-amber-500/15 text-amber-300" },
  SELL: { bg: "bg-red-500/8",      border: "border-red-500/30",     text: "text-red-400",     badge: "bg-red-500/15 text-red-300" },
};

const CONVICTION_DOT: Record<string, string> = {
  HIGH: "bg-emerald-400",
  MEDIUM: "bg-amber-400",
  LOW: "bg-slate-400",
};

const RISK_COLOR: Record<string, string> = {
  LOW: "text-emerald-400",
  MEDIUM: "text-amber-400",
  HIGH: "text-orange-400",
  VERY_HIGH: "text-red-400",
};

export default function DecisionBanner({ result, onDownload }: { result: any; onDownload: () => void }) {
  const decision = result.decision || "HOLD";
  const style = DECISION_STYLES[decision] || DECISION_STYLES.HOLD;
  const conviction = result.conviction || "LOW";
  const riskRating = result.agent_outputs?.risk_manager?.risk_rating || "N/A";

  return (
    <div className={`rounded-2xl border ${style.bg} ${style.border} p-6`}>
      <div className="flex flex-col lg:flex-row lg:items-start gap-6">
        {/* Left: decision */}
        <div className="flex items-center gap-5 shrink-0">
          <div className="text-center">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Decision</div>
            <div className={`text-5xl font-bold ${style.text} tracking-tight mono`}>{decision}</div>
          </div>
          <div className="w-px h-14 bg-slate-800"></div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${CONVICTION_DOT[conviction] || "bg-slate-400"}`}></span>
              <span className="text-slate-400 text-xs">Conviction</span>
              <span className="text-white text-xs font-semibold">{conviction}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-xs">Target weight</span>
              <span className="text-white text-xs font-semibold mono">{result.target_weight || "0%"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-xs">Risk</span>
              <span className={`text-xs font-semibold ${RISK_COLOR[riskRating] || "text-slate-400"}`}>{riskRating}</span>
            </div>
          </div>
        </div>

        {/* Center: thesis */}
        {result.key_thesis && (
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Investment Thesis</div>
            <p className="text-slate-200 text-sm leading-relaxed">{result.key_thesis}</p>
          </div>
        )}

        {/* Right: badges + actions */}
        <div className="flex flex-col gap-3 shrink-0 items-end">
          <div className="flex flex-wrap gap-2">
            {result.credit_score != null && (
              <div className="flex flex-col items-center bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-2 min-w-[80px]">
                <span className="text-slate-500 text-xs">Credit</span>
                <span className={`font-bold text-xl mono ${
                  result.credit_score >= 75 ? "text-emerald-400" :
                  result.credit_score >= 50 ? "text-amber-400" : "text-red-400"
                }`}>{Math.round(result.credit_score)}</span>
                <span className="text-slate-600 text-xs">/100</span>
              </div>
            )}
            {result.regime && (
              <div className="flex flex-col items-center bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-2 min-w-[80px]">
                <span className="text-slate-500 text-xs">Regime</span>
                <span className={`font-bold text-sm mt-1 ${
                  result.regime === "BULL" ? "text-emerald-400" :
                  result.regime === "BEAR" ? "text-red-400" : "text-amber-400"
                }`}>{result.regime === "BULL" ? "↑" : result.regime === "BEAR" ? "↓" : "→"} {result.regime}</span>
              </div>
            )}
          </div>
          <button
            onClick={onDownload}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm text-slate-300 hover:text-white transition-all duration-200"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            SFDR Report
          </button>
        </div>
      </div>
    </div>
  );
}
