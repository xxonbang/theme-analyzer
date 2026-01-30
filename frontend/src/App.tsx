import { useEffect, useState, lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Navigation } from '@/components/common';
import { Hero, AnalysisTabs, Footer } from '@/components/layout';
import { HistoryPanel } from '@/components/history';
import { VisionAnalysis, APIAnalysis } from '@/pages';
import { LoadingSpinner } from '@/components/common';

// CombinedAnalysis는 lazy loading - 처음 접근 시에만 로드
const CombinedAnalysis = lazy(() => import('@/pages/CombinedAnalysis').then(m => ({ default: m.CombinedAnalysis })));
import { useUIStore } from '@/store/uiStore';
import { fetchLatestData, fetchKISData, fetchKISAnalysis, fetchHistoryIndex } from '@/services/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5분간 데이터를 fresh로 유지
    },
  },
});

// 앱 로드 시 모든 데이터를 미리 prefetch하는 훅
function usePrefetchAllData() {
  const client = useQueryClient();

  useEffect(() => {
    // 백그라운드에서 모든 데이터 prefetch (병렬 실행)
    Promise.allSettled([
      client.prefetchQuery({
        queryKey: ['vision', 'latest'],
        queryFn: fetchLatestData,
      }),
      client.prefetchQuery({
        queryKey: ['kis-data'],
        queryFn: fetchKISData,
      }),
      client.prefetchQuery({
        queryKey: ['kis-analysis'],
        queryFn: fetchKISAnalysis,
      }),
      client.prefetchQuery({
        queryKey: ['history', 'index'],
        queryFn: fetchHistoryIndex,
      }),
    ]);
  }, [client]);
}

function FeaturesSection() {
  return (
    <section id="features" className="mb-8 md:mb-10">
      <div className="mb-4 md:mb-5">
        <h2 className="text-lg md:text-xl font-bold text-text-primary">주요 기능</h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
        <div className="bg-bg-secondary border border-border rounded-xl p-3 md:p-5 transition-all hover:border-accent-primary hover:shadow-md hover:-translate-y-0.5">
          <div className="w-9 h-9 md:w-11 md:h-11 rounded-lg bg-blue-100 flex items-center justify-center text-base md:text-xl mb-2 md:mb-3">
            📊
          </div>
          <h3 className="text-sm md:text-base font-bold mb-1 md:mb-1.5">실시간 데이터 수집</h3>
          <p className="text-xs md:text-sm text-text-secondary leading-relaxed">
            <span className="hidden sm:inline">네이버 증권 API에서 </span>거래량 상위 120개 종목<span className="hidden sm:inline">을 실시간으로</span> 수집
          </p>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl p-3 md:p-5 transition-all hover:border-accent-primary hover:shadow-md hover:-translate-y-0.5">
          <div className="w-9 h-9 md:w-11 md:h-11 rounded-lg bg-cyan-100 flex items-center justify-center text-base md:text-xl mb-2 md:mb-3">
            📸
          </div>
          <h3 className="text-sm md:text-base font-bold mb-1 md:mb-1.5">고해상도 스크린샷</h3>
          <p className="text-xs md:text-sm text-text-secondary leading-relaxed">
            Playwright로 <span className="hidden sm:inline">각 </span>종목 상세 페이지<span className="hidden sm:inline">를 고해상도로</span> 캡처
          </p>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl p-3 md:p-5 transition-all hover:border-accent-primary hover:shadow-md hover:-translate-y-0.5">
          <div className="w-9 h-9 md:w-11 md:h-11 rounded-lg bg-teal-100 flex items-center justify-center text-base md:text-xl mb-2 md:mb-3">
            🤖
          </div>
          <h3 className="text-sm md:text-base font-bold mb-1 md:mb-1.5">AI 배치 분석</h3>
          <p className="text-xs md:text-sm text-text-secondary leading-relaxed">
            120개 이미지<span className="hidden sm:inline">를 한 번에 분석하여 API 효율을</span> 배치 분석
          </p>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl p-3 md:p-5 transition-all hover:border-accent-primary hover:shadow-md hover:-translate-y-0.5">
          <div className="w-9 h-9 md:w-11 md:h-11 rounded-lg bg-amber-100 flex items-center justify-center text-base md:text-xl mb-2 md:mb-3">
            📈
          </div>
          <h3 className="text-sm md:text-base font-bold mb-1 md:mb-1.5">5단계 시그널</h3>
          <p className="text-xs md:text-sm text-text-secondary leading-relaxed">
            적극매수~적극매도 5단계 시그널<span className="hidden sm:inline">과 분석 근거 제공</span>
          </p>
        </div>
      </div>
    </section>
  );
}

function WorkflowSection() {
  return (
    <section className="bg-bg-secondary border border-border rounded-xl md:rounded-2xl p-4 md:p-6 mb-8 md:mb-10">
      <h2 className="text-lg md:text-xl font-bold text-center mb-4 md:mb-5">분석 워크플로우</h2>
      <div className="grid grid-cols-4 gap-2 md:gap-4">
        <div className="text-center relative">
          <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-full flex items-center justify-center mx-auto mb-1.5 md:mb-2.5 text-white text-sm md:text-base font-bold">
            1
          </div>
          <h4 className="text-xs md:text-sm font-bold mb-0.5 md:mb-1">수집</h4>
          <p className="text-[0.6rem] md:text-xs text-text-muted hidden sm:block">상위 120개 종목</p>
          <span className="hidden md:block absolute top-5 right-0 translate-x-1/2 text-border">→</span>
        </div>
        <div className="text-center relative">
          <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-full flex items-center justify-center mx-auto mb-1.5 md:mb-2.5 text-white text-sm md:text-base font-bold">
            2
          </div>
          <h4 className="text-xs md:text-sm font-bold mb-0.5 md:mb-1">캡처</h4>
          <p className="text-[0.6rem] md:text-xs text-text-muted hidden sm:block">풀스크린 캡처</p>
          <span className="hidden md:block absolute top-5 right-0 translate-x-1/2 text-border">→</span>
        </div>
        <div className="text-center relative">
          <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-full flex items-center justify-center mx-auto mb-1.5 md:mb-2.5 text-white text-sm md:text-base font-bold">
            3
          </div>
          <h4 className="text-xs md:text-sm font-bold mb-0.5 md:mb-1">분석</h4>
          <p className="text-[0.6rem] md:text-xs text-text-muted hidden sm:block">배치 이미지 분석</p>
          <span className="hidden md:block absolute top-5 right-0 translate-x-1/2 text-border">→</span>
        </div>
        <div className="text-center">
          <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-full flex items-center justify-center mx-auto mb-1.5 md:mb-2.5 text-white text-sm md:text-base font-bold">
            4
          </div>
          <h4 className="text-xs md:text-sm font-bold mb-0.5 md:mb-1">리포트</h4>
          <p className="text-[0.6rem] md:text-xs text-text-muted hidden sm:block">결과 저장 (30일)</p>
        </div>
      </div>
    </section>
  );
}

function MainContent() {
  const { activeTab } = useUIStore();

  // 지연 마운트: 탭을 한 번이라도 방문했는지 추적
  // 방문한 탭만 렌더링하고, 이후에는 CSS로 숨김 처리
  const [mountedTabs, setMountedTabs] = useState<Set<string>>(() => new Set(['vision']));

  useEffect(() => {
    if (!mountedTabs.has(activeTab)) {
      setMountedTabs(prev => new Set([...prev, activeTab]));
    }
  }, [activeTab, mountedTabs]);

  return (
    <>
      <AnalysisTabs />

      {/* Vision AI - 항상 마운트 */}
      <div style={{ display: activeTab === 'vision' ? 'block' : 'none' }}>
        <VisionAnalysis />
      </div>

      {/* API Analysis - 방문 시에만 마운트 */}
      {mountedTabs.has('api') && (
        <div style={{ display: activeTab === 'api' ? 'block' : 'none' }}>
          <APIAnalysis />
        </div>
      )}

      {/* Combined Analysis - 방문 시에만 마운트 (lazy loading) */}
      {mountedTabs.has('combined') && (
        <div style={{ display: activeTab === 'combined' ? 'block' : 'none' }}>
          <Suspense fallback={<LoadingSpinner message="분석 종합 로딩 중..." />}>
            <CombinedAnalysis />
          </Suspense>
        </div>
      )}
    </>
  );
}

function AppContent() {
  // 앱 로드 시 모든 데이터 미리 로드
  usePrefetchAllData();

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      <Navigation />
      <HistoryPanel />

      <main className="max-w-[1200px] mx-auto px-4 md:px-6 pt-20 md:pt-24 pb-10">
        <Hero />
        <MainContent />
        <FeaturesSection />
        <WorkflowSection />
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
