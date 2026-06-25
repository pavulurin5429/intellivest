"use client";

const STEPS = [
  { label: "Fetching SEC EDGAR filings", icon: "📄" },
  { label: "Pulling price history & ratios", icon: "📊" },
  { label: "Scoring news sentiment (FinBERT)", icon: "🧠" },
  { label: "Computing credit scorecard", icon: "💳" },
  { label: "Running 5-agent debate", icon: "🤖" },
  { label: "Fund Manager synthesising decision", icon: "⚖️" },
];

export default function AnalysisLoader({ ticker }: { ticker: string }) {
  return (
    <div className="max-w-2xl mx-auto animate-slide-up">
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <div>
            <p className="text-white font-semibold">Analysing <span className="text-blue-400 mono">{ticker}</span></p>
            <p className="text-slate-500 text-sm">Multi-agent pipeline running — takes ~60s</p>
          </div>
        </div>
        <div className="space-y-3">
          {STEPS.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-base w-6 text-center">{step.icon}</span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full animate-pulse-slow"
                  style={{
                    width: `${Math.min(100, (i + 1) * 17)}%`,
                    animationDelay: `${i * 0.2}s`,
                  }}
                ></div>
              </div>
              <span className="text-slate-500 text-xs w-40 shrink-0">{step.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
