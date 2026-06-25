const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function triggerAnalysis(ticker: string) {
  const res = await fetch(`${API_URL}/api/analyze/${ticker}`, { method: "POST" });
  return res.json();
}

export async function getAnalysisStatus(ticker: string) {
  const res = await fetch(`${API_URL}/api/analyze/status/${ticker}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getCreditScore(ticker: string) {
  const res = await fetch(`${API_URL}/api/credit/${ticker}`);
  if (!res.ok) return null;
  return res.json();
}

export function downloadReport(ticker: string) {
  window.open(`${API_URL}/api/reports/${ticker}/pdf`, "_blank");
}
