import type { AnalysisData, HistoryIndex, KISGeminiData, KISAnalysisData } from './types';

const BASE_URL = import.meta.env.DEV ? '' : '.';

export async function fetchLatestData(): Promise<AnalysisData> {
  const response = await fetch(`${BASE_URL}/results/latest.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch latest data');
  }
  return response.json();
}

export async function fetchHistoryData(filename: string): Promise<AnalysisData> {
  const response = await fetch(`${BASE_URL}/results/history/${filename}`);
  if (!response.ok) {
    throw new Error('Failed to fetch history data');
  }
  return response.json();
}

export async function fetchHistoryIndex(): Promise<HistoryIndex> {
  const response = await fetch(`${BASE_URL}/results/history_index.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch history index');
  }
  return response.json();
}

// KIS API 데이터 fetch 함수들
export async function fetchKISData(): Promise<KISGeminiData> {
  const response = await fetch(`${BASE_URL}/results/kis/latest.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch KIS data');
  }
  return response.json();
}

export async function fetchKISAnalysis(): Promise<KISAnalysisData> {
  const response = await fetch(`${BASE_URL}/results/kis/analysis.json`);
  if (!response.ok) {
    throw new Error('Failed to fetch KIS analysis');
  }
  return response.json();
}
