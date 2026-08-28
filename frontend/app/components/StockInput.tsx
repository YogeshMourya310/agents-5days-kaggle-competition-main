'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, TrendingUp } from 'lucide-react';

interface StockInputProps {
  onAnalyze: (ticker: string) => void;
  isLoading: boolean;
}

export default function StockInput({ onAnalyze, isLoading }: StockInputProps) {
  const [input, setInput] = useState('');
  const [focused, setFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onAnalyze(input.trim().toUpperCase());
    }
  };

  const popularStocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'BAJAJ-AUTO'];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto mb-12"
    >
      <div className="glass rounded-3xl p-8 hover:shadow-glow transition-all duration-500">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-white">Analyze NSE Stocks</h2>
            <p className="text-slate-400 text-sm">
              Enter an NSE symbol like <span className="text-cyan-400 font-semibold">RELIANCE</span> or{' '}
              <span className="text-cyan-400 font-semibold">TCS</span>.
            </p>
          </div>

          <div className="relative">
            <div
              className={`relative rounded-2xl transition-all duration-300 ${focused ? 'ring-2 ring-cyan-500/50' : ''}`}
            >
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className={`w-6 h-6 transition-colors ${focused ? 'text-cyan-400' : 'text-gray-400'}`} />
              </div>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="Enter NSE ticker (e.g., RELIANCE, INFY, M&M)"
                className="
                  w-full pl-14 pr-4 py-5
                  bg-slate-950/80 border border-slate-700/50
                  rounded-2xl text-white placeholder-slate-500
                  focus:outline-none focus:border-cyan-500/50 focus:bg-slate-900/90
                  focus:shadow-glow-sm
                  transition-all duration-300 text-lg font-medium
                  tracking-wide
                "
                disabled={isLoading}
              />
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            type="submit"
            disabled={!input.trim() || isLoading}
            className="
              relative w-full py-5 px-6 rounded-2xl overflow-hidden
              bg-gradient-to-r from-emerald-600 via-teal-500 to-cyan-500
              hover:from-emerald-500 hover:via-teal-400 hover:to-cyan-400
              disabled:from-slate-800 disabled:to-slate-700
              disabled:cursor-not-allowed
              text-white font-bold text-lg
              shadow-lg shadow-cyan-500/20
              transition-all duration-300
              flex items-center justify-center gap-3
              group
            "
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover:translate-x-full transition-transform duration-1000" />
            <TrendingUp className="w-5 h-5 relative z-10" />
            <span className="relative z-10">Run NSE Analysis</span>
          </motion.button>

          <div className="space-y-3">
            <p className="text-sm text-slate-500 text-center font-medium">Popular NSE names:</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {popularStocks.map((stock) => (
                <motion.button
                  key={stock}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  type="button"
                  onClick={() => setInput(stock)}
                  className="
                    px-5 py-2.5 rounded-xl
                    bg-slate-800/50 hover:bg-slate-700/70
                    border border-slate-700/50 hover:border-cyan-500/50
                    text-sm font-semibold text-slate-300 hover:text-white
                    transition-all duration-300
                  "
                  disabled={isLoading}
                >
                  {stock}
                </motion.button>
              ))}
            </div>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-800/50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-xs font-semibold text-slate-400">NSE-focused analysis</div>
            </div>
            <div className="text-center">
              <div className="text-xs font-semibold text-slate-400">Technical, macro, and disclosure context</div>
            </div>
            <div className="text-center">
              <div className="text-xs font-semibold text-slate-400">Investor-friendly output</div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
