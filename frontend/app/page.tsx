'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, Sparkles, AlertCircle, BarChart3, Clock, Award, Bot } from 'lucide-react';
import { FaChartLine, FaChartBar, FaNewspaper, FaGlobeAmericas, FaBalanceScale } from 'react-icons/fa';

import StockInput from './components/StockInput';
import OrchestratorCard from './components/OrchestratorCard';
import AgentCard from './components/AgentCard';
import AgentDetailModal from './components/AgentDetailModal';
import ResultsPanel from './components/ResultsPanel';
import InvestorAdvisorCard from './components/InvestorAdvisorCard';
import TradingViewWidget from './components/TradingViewWidget';
import { AgentStatus, AnalysisResult, OrchestratorStatus } from './types';

const AGENTS = [
  { id: 'fundamental', name: 'Fundamental Analyst', icon: FaChartLine, color: 'from-blue-500 to-cyan-500' },
  { id: 'technical', name: 'Technical Analyst', icon: FaChartBar, color: 'from-green-500 to-emerald-500' },
  { id: 'sentiment', name: 'Sentiment Analyst', icon: FaNewspaper, color: 'from-pink-500 to-rose-500' },
  { id: 'macro', name: 'Macro Analyst', icon: FaGlobeAmericas, color: 'from-orange-500 to-red-500' },
  { id: 'regulatory', name: 'Regulatory Analyst', icon: FaBalanceScale, color: 'from-yellow-500 to-amber-500' },
];

export default function Home() {
  const [ticker, setTicker] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [orchestratorStatus, setOrchestratorStatus] = useState<OrchestratorStatus>({
    status: 'idle',
    message: 'Ready to analyze NSE stocks',
    progress: 0,
  });
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>(
    AGENTS.map((agent) => ({ id: agent.id, name: agent.name, status: 'idle', progress: 0 }))
  );
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [investorAdvice, setInvestorAdvice] = useState<string | null>(null);
  const [isGeneratingAdvice, setIsGeneratingAdvice] = useState(false);
  const [adviceError, setAdviceError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentStatus | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleAnalyze = async (inputTicker: string) => {
    setTicker(inputTicker.toUpperCase());
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    setInvestorAdvice(null);

    setOrchestratorStatus({ status: 'initializing', message: 'Preparing NSE analysis pipeline...', progress: 10 });
    setAgentStatuses((prev) => prev.map((agent) => ({ ...agent, status: 'idle', progress: 0 })));

    try {
      await new Promise((resolve) => setTimeout(resolve, 700));
      setOrchestratorStatus({ status: 'analyzing', message: 'Running specialist agents...', progress: 35 });
      setAgentStatuses((prev) => prev.map((agent) => ({ ...agent, status: 'working', progress: 20 })));

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: inputTicker.toUpperCase(), horizon: 'next_quarter' }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const data: AnalysisResult = await response.json();

      setAgentStatuses((prev) =>
        prev.map((agent) => {
          const agentData = data.analysis_reports[agent.id];
          return {
            ...agent,
            status: agentData ? 'completed' : 'error',
            progress: 100,
            signal: agentData?.directional_signal,
            confidence: agentData?.confidence_score,
            summary: agentData?.summary,
            keyMetrics: agentData?.key_metrics,
          };
        })
      );

      setOrchestratorStatus({ status: 'synthesizing', message: 'Synthesizing final NSE recommendation...', progress: 80 });
      await new Promise((resolve) => setTimeout(resolve, 700));
      setOrchestratorStatus({ status: 'completed', message: 'Analysis complete', progress: 100 });
      setResult(data);

      try {
        const historyEntry = { ...data, id: `${data.ticker}-${Date.now()}`, timestamp: new Date().toISOString() };
        const existingHistory = localStorage.getItem('analysis_history');
        const history = existingHistory ? JSON.parse(existingHistory) : [];
        history.unshift(historyEntry);
        if (history.length > 50) history.length = 50;
        localStorage.setItem('analysis_history', JSON.stringify(history));
      } catch (storageErr) {
        console.error('Failed to save to history:', storageErr);
      }

      setIsGeneratingAdvice(true);
      setAdviceError(null);
      try {
        const adviceResponse = await fetch('/api/investor-advice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ analysis: data }),
        });
        const adviceData = await adviceResponse.json();
        if (adviceResponse.ok) {
          setInvestorAdvice(adviceData.advice);
        } else {
          setAdviceError(adviceData.detail || 'Failed to generate advice');
        }
      } catch (adviceErr: any) {
        setAdviceError(adviceErr.message || 'Network error generating advice');
      } finally {
        setIsGeneratingAdvice(false);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis');
      setOrchestratorStatus({ status: 'error', message: 'Analysis failed', progress: 0 });
      setAgentStatuses((prev) => prev.map((agent) => ({ ...agent, status: 'error', progress: 0 })));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    setTicker('');
    setResult(null);
    setError(null);
    setInvestorAdvice(null);
    setIsGeneratingAdvice(false);
    setSelectedAgent(null);
    setIsModalOpen(false);
    setOrchestratorStatus({ status: 'idle', message: 'Ready to analyze NSE stocks', progress: 0 });
    setAgentStatuses((prev) => prev.map((agent) => ({ ...agent, status: 'idle', progress: 0 })));
  };

  return (
    <main className="min-h-screen p-4 md:p-8 relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-emerald-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-cyan-600/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm text-emerald-400 font-medium">NSE-focused Multi-Agent Analysis</span>
          </div>

          <div className="flex items-center justify-center gap-4 mb-5">
            <Sparkles className="w-10 h-10 text-emerald-500" />
            <h1 className="text-5xl md:text-7xl font-bold gradient-text tracking-tight">AI NSE Stock Predictor</h1>
            <TrendingUp className="w-10 h-10 text-cyan-500" />
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 mb-3">
            <p className="text-slate-300 text-lg md:text-xl font-light">Fundamental, technical, macro, sentiment, and disclosure signals for Indian equities</p>
          </div>
          <p className="text-slate-500 text-sm">Built for NSE-style symbols like RELIANCE, TCS, INFY, HDFCBANK, and M&amp;M</p>
        </motion.div>

        {!isAnalyzing && !result && (
          <>
            <StockInput onAnalyze={handleAnalyze} isLoading={false} />
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-wrap gap-4 justify-center mt-6"
            >
              <a href="/compare" className="flex items-center gap-2 px-6 py-3 glass hover:bg-slate-800/50 rounded-xl transition-all font-semibold">
                <BarChart3 className="w-5 h-5" />
                Compare Stocks
              </a>
              <a href="/history" className="flex items-center gap-2 px-6 py-3 glass hover:bg-slate-800/50 rounded-xl transition-all font-semibold">
                <Clock className="w-5 h-5" />
                View History
              </a>
              <a
                href="/capabilities"
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-600/20 to-cyan-600/20 border border-emerald-500/30 rounded-xl transition-all font-semibold"
              >
                <Award className="w-5 h-5 text-emerald-400" />
                System Capabilities
              </a>
            </motion.div>
          </>
        )}

        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="mb-8 glass p-6 rounded-2xl border-red-500/50">
              <div className="flex items-center gap-3 text-red-400">
                <AlertCircle className="w-6 h-6" />
                <div>
                  <h3 className="font-semibold">Analysis Error</h3>
                  <p className="text-sm text-gray-300">{error}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {(isAnalyzing || result) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              <OrchestratorCard ticker={ticker} status={orchestratorStatus} />

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agentStatuses.map((agent, index) => {
                  const agentConfig = AGENTS.find((a) => a.id === agent.id);
                  return (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      icon={agentConfig?.icon || Bot}
                      color={agentConfig?.color || 'from-gray-500 to-gray-600'}
                      delay={index * 0.1}
                      onViewDetails={() => {
                        setSelectedAgent(agent);
                        setIsModalOpen(true);
                      }}
                    />
                  );
                })}
              </div>

              {result && (
                <>
                  <ResultsPanel result={result} onReset={handleReset} />
                  <TradingViewWidget ticker={ticker} />
                  <InvestorAdvisorCard advice={investorAdvice} isGenerating={isGeneratingAdvice} error={adviceError} ticker={ticker} />
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          icon={AGENTS.find((a) => a.id === selectedAgent.id)?.icon || (() => null)}
          color={AGENTS.find((a) => a.id === selectedAgent.id)?.color || 'from-gray-500 to-gray-600'}
        />
      )}
    </main>
  );
}
