"use client";

const RATING_STYLE: Record<string, { text: string; bg: string; border: string }> = {
  LOW:       { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/25" },
  MEDIUM:    { text: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/25" },
  HIGH:      { text: "text-orange-400",  bg: "bg-orange-500/10",  border: "border-orange-500/25" },
  VERY_HIGH: { text: "text-red-400",     bg: "bg-red-500/10",     border: "border-red-500/25" },
};

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
      <p className="text-slate-500 text-xs mb-1">{label}</p>
      <p className="text-white font-semibold mono text-sm">{value}</p>
      {sub && <p className="text-slate-600 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

export default function RiskMetrics({ riskOutput }: { riskOutput: any }) {
  if (!riskOutput) return null;
  const v = riskOutput.var_metrics || {};
  const rating = riskOutput.risk_rating || "N/A";
  const style = RATING_STYLE[rating] || { text: "text-slate-400", bg: "bg-slate-800", border: "border-slate-700" };

  const fmt = (n: number | undefined) => n != null ? `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}` : "N/A";
  const pct = (n: number | undefined) => n != null ? `${(n * 100).toFixed(1)}%` : "N/A";

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden h-fit">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <h2 className="text-white text-sm font-semibold">Risk Metrics</h2>
        </div>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-lg mono ${style.text} ${style.bg} border ${style.border}`}>
          {rating}
        </span>
      </div>

      <div className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <MetricCard label="VaR 95% (1-day)" value={fmt(v.historical_var_95)} sub="Historical" />
          <MetricCard label="CVaR / ES (95%)" value={fmt(v.cvar_95)} sub="Expected shortfall" />
          <MetricCard label="Max Drawdown" value={pct(v.max_drawdown)} />
          <MetricCard label="Annual Volatility" value={pct(v.annual_vol)} />
        </div>

        {riskOutput.max_position_size && (
          <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3 border border-slate-700/50">
            <span className="text-slate-400 text-xs">Max recommended position</span>
            <span className="text-white font-bold mono">{riskOutput.max_position_size}</span>
          </div>
        )}

        {riskOutput.key_risks?.length > 0 && (
          <div>
            <p className="text-slate-500 text-xs uppercase tracking-wider mb-2">Key risks</p>
            <div className="space-y-1.5">
              {riskOutput.key_risks.filter(Boolean).map((r: string, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-rose-400 mt-1.5 shrink-0"></span>
                  <span className="text-slate-400 text-xs">{r}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
