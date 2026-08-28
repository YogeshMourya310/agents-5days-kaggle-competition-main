'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, TrendingUp, Shield, Clock, RotateCcw, ChevronDown } from 'lucide-react';

import { AnalysisResult } from '../types';
import AgentRadarChart from './AgentRadarChart';
import ConfidenceGauge from './ConfidenceGauge';

interface ResultsPanelProps {
  result: AnalysisResult;
  onReset: () => void;
}

const formatLabel = (key: string): string =>
  key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

export default function ResultsPanel({ result, onReset }: ResultsPanelProps) {
  const [showDetails, setShowDetails] = useState(false);
  const elapsed = result.elapsed_seconds ?? result.elapsed_time_seconds ?? 0;

  const recommendationColor =
    result.recommendation === 'BUY'
      ? 'from-green-500 to-emerald-400'
      : result.recommendation === 'SELL'
        ? 'from-red-500 to-pink-400'
        : 'from-yellow-500 to-orange-400';

  const riskColor =
    result.risk_level === 'LOW'
      ? 'text-green-400'
      : result.risk_level === 'HIGH'
        ? 'text-red-400'
        : 'text-yellow-400';

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="glass rounded-3xl p-10">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-blue-400" />
            <div>
              <h2 className="text-3xl font-bold text-white">NSE Final View</h2>
              <p className="text-sm text-slate-400">Combined signal for {result.ticker}</p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onReset}
            className="glass-dark px-5 py-3 rounded-xl flex items-center gap-2 text-sm font-semibold"
          >
            <RotateCcw className="w-4 h-4" />
            New Analysis
          </motion.button>
        </div>

        <div className="mb-10">
          <div className={`inline-block px-12 py-6 rounded-3xl bg-gradient-to-r ${recommendationColor}`}>
            <div className="text-sm font-semibold text-white/80 mb-2 uppercase tracking-wider">
              Recommendation for {result.ticker}
            </div>
            <div className="text-6xl font-black text-white tracking-tight">{result.recommendation}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
          <div className="glass-dark rounded-2xl p-6">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-3 font-semibold uppercase tracking-wider">
              <TrendingUp className="w-4 h-4" />
              Confidence
            </div>
            <div className="text-4xl font-black text-blue-400">{result.confidence.toFixed(1)}%</div>
          </div>

          <div className="glass-dark rounded-2xl p-6">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-3 font-semibold uppercase tracking-wider">
              <Shield className="w-4 h-4" />
              Risk Level
            </div>
            <div className={`text-4xl font-black ${riskColor}`}>{result.risk_level}</div>
          </div>

          <div className="glass-dark rounded-2xl p-6">
            <div className="text-slate-500 text-xs mb-3 font-semibold uppercase tracking-wider">Signal Strength</div>
            <div className="text-4xl font-black text-purple-400">
              {result.weighted_signal >= 0 ? '+' : ''}
              {result.weighted_signal.toFixed(3)}
            </div>
          </div>

          <div className="glass-dark rounded-2xl p-6">
            <div className="flex items-center gap-2 text-slate-500 text-xs mb-3 font-semibold uppercase tracking-wider">
              <Clock className="w-4 h-4" />
              Analysis Time
            </div>
            <div className="text-4xl font-black text-cyan-400">{elapsed.toFixed(1)}s</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <AgentRadarChart result={result} />
          <ConfidenceGauge confidence={result.confidence} />
        </div>

        <div className="glass-dark rounded-2xl p-6 border border-slate-800/50">
          <h3 className="text-lg font-bold mb-5 flex items-center gap-2 text-white">
            <Sparkles className="w-5 h-5 text-blue-400" />
            NSE Analysis Rationale
          </h3>
          <div className="space-y-3 leading-relaxed text-base text-slate-300 whitespace-pre-line">
            {result.rationale || 'Based on combined fundamental, technical, sentiment, macro, and disclosure analysis.'}
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => setShowDetails(!showDetails)}
          className="w-full mt-6 glass-dark px-6 py-4 rounded-xl flex items-center justify-center gap-2 font-semibold"
        >
          <span className="text-sm">{showDetails ? 'Hide' : 'Show'} Detailed Agent Responses</span>
          <motion.div animate={{ rotate: showDetails ? 180 : 0 }} transition={{ duration: 0.3 }}>
            <ChevronDown className="w-5 h-5" />
          </motion.div>
        </motion.button>
      </div>

      <motion.div
        initial={false}
        animate={{ height: showDetails ? 'auto' : 0, opacity: showDetails ? 1 : 0 }}
        transition={{ duration: 0.3 }}
        className="overflow-hidden"
      >
        <div className="space-y-5">
          {Object.entries(result.analysis_reports).map(([agentId, response], index) => (
            <motion.div
              key={agentId}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glass rounded-2xl p-7"
            >
              <div className="flex items-start justify-between mb-5">
                <div>
                  <h4 className="font-bold text-xl capitalize text-white">{agentId.replace('_', ' ')}</h4>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="text-sm font-semibold text-slate-400">
                      Signal: <span className="text-blue-400">{response.directional_signal.toFixed(2)}</span>
                    </span>
                    <span className="text-sm font-semibold text-slate-400">
                      Confidence: <span className="text-cyan-400">{response.confidence_score.toFixed(1)}%</span>
                    </span>
                  </div>
                </div>
                {response.data_source && (
                  <span className="text-xs font-semibold text-slate-500 bg-slate-800/50 px-4 py-2 rounded-full">
                    {response.data_source}
                  </span>
                )}
              </div>

              {response.summary && <p className="text-sm text-slate-300 mb-5 leading-relaxed">{response.summary}</p>}

              {response.key_metrics && Object.keys(response.key_metrics).length > 0 && (
                <div className="glass-dark rounded-xl p-5 border border-slate-800/50">
                  <div className="text-xs text-slate-500 mb-3 font-semibold uppercase tracking-wider">Key Metrics</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(response.key_metrics)
                      .filter(([_, value]) => typeof value !== 'object')
                      .map(([key, value]) => (
                        <div key={key}>
                          <div className="text-xs text-slate-500 mb-1 font-medium">{formatLabel(key)}</div>
                          <div className="text-sm font-bold text-white">
                            {typeof value === 'number' ? value.toFixed(2) : String(value)}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
