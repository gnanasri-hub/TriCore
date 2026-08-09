import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Activity, TrendingUp, ShieldAlert, Award, ChevronRight, Sparkles, BookOpen } from 'lucide-react';

// Dynamic mapper translating knowledge gaps into actionable, professional engineering suggestions
const getTechnicalSuggestions = (gaps) => {
  if (!gaps || gaps.length === 0) return [];
  
  return gaps.map(gap => {
    const text = gap.toLowerCase();
    if (text.includes("sql") || text.includes("database") || text.includes("postgres")) {
      return "Study query optimization, index patterns, and transactional isolation bounds.";
    }
    if (text.includes("rag") || text.includes("vector") || text.includes("embedding")) {
      return "Analyze chunk chunk-size splitting boundaries and study hybrid keyword/vector search.";
    }
    if (text.includes("agent") || text.includes("langchain") || text.includes("mcp")) {
      return "Investigate Model Context Protocol tools and state machine orchestrations.";
    }
    if (text.includes("cache") || text.includes("redis")) {
      return "Implement write-through caching layers and key lifecycle expiration boundaries.";
    }
    if (text.includes("git") || text.includes("version")) {
      return "Refine commit squashing practices and merge conflict resolution protocols.";
    }
    if (text.includes("api") || text.includes("fastapi") || text.includes("http")) {
      return "Standardize request schemas using Pydantic and define robust route models.";
    }
    // Fallback dynamic suggestion
    const keywords = gap.split(' ').slice(0, 3).join(' ');
    return `Deepen competency in related cohort objectives; focus on resolving ${keywords}.`;
  });
};

export default function LiveFeedbackPanel({ evaluation, sessionStatus }) {
  const accuracy = evaluation?.technical_accuracy ?? null;
  const depthScore = evaluation?.depth ?? null;
  const clarity = evaluation?.clarity ?? null;
  
  // Slice to max 3 points per category
  const strengths = (evaluation?.strengths || []).slice(0, 3);
  const gaps = (evaluation?.missing_points || []).slice(0, 3);
  const suggestions = getTechnicalSuggestions(evaluation?.missing_points || []).slice(0, 3);

  const confidence = accuracy === null ? 'Waiting...' : accuracy >= 8 ? 'High' : accuracy >= 6 ? 'Medium' : 'Low';
  const depth = depthScore === null ? 'Waiting...' : depthScore >= 7 ? 'Strong' : 'Weak';
  const clarityScore = clarity === null ? null : clarity * 10;

  const questionCount = sessionStatus?.question_count || 1;
  const isPendingFollowUp = sessionStatus?.pending_follow_up?.is_pending || false;
  const mood = questionCount <= 1 ? 'Neutral' : isPendingFollowUp ? 'Curious' : 'Challenging';
  const difficulty = accuracy !== null && accuracy >= 8 ? 'Hard' : 'Standard';

  // Stagger animations sliding from right
  const listVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: 20 },
    show: { 
      opacity: 1, 
      x: 0, 
      transition: { type: "spring", stiffness: 180, damping: 15 } 
    }
  };

  return (
    <div className="w-full flex flex-col gap-6 select-none h-full overflow-y-auto pr-1">
      {/* ── Intelligence Header ── */}
      <div className="flex items-center gap-2 pb-1 border-b border-zinc-900">
        <Brain className="text-purple-400 shrink-0" size={18} />
        <span className="font-bold text-xs tracking-widest uppercase font-display text-zinc-400">AI Adaptive Core</span>
        <div className="ml-auto w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
      </div>

      {/* ── AI Mood & Difficulty Indicators ── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-card p-4 rounded-xl border-zinc-800/80 flex flex-col gap-1.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">AI Mood State</span>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${mood === 'Challenging' ? 'bg-red-500' : mood === 'Curious' ? 'bg-amber-500' : 'bg-purple-500'}`} />
            <span className="font-display font-extrabold text-[14px] text-zinc-200">{mood}</span>
          </div>
        </div>

        <div className="glass-card p-4 rounded-xl border-zinc-800/80 flex flex-col gap-1.5">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Target Tier</span>
          <div className="flex items-center gap-2">
            <TrendingUp className={`shrink-0 ${difficulty === 'Hard' ? 'text-pink-500' : 'text-blue-400'}`} size={16} />
            <span className="font-display font-extrabold text-[14px] text-zinc-200">{difficulty}</span>
          </div>
        </div>
      </div>

      {/* ── Live Adaptive Signals ── */}
      <div className="glass-card p-5 rounded-2xl border-zinc-850/80 space-y-4">
        <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-extrabold block">Live Feedback Signals</span>
        <div className="space-y-3">
          <div className="flex justify-between items-center bg-zinc-950/40 p-2.5 rounded-xl border border-zinc-900/60">
            <span className="text-xs text-zinc-400 font-medium">Confidence Rating</span>
            <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
              confidence === 'High' ? 'bg-emerald-950/30 text-emerald-400' : confidence === 'Medium' ? 'bg-blue-950/30 text-blue-400' : 'bg-red-950/30 text-red-400'
            }`}>{confidence}</span>
          </div>
          <div className="flex justify-between items-center bg-zinc-950/40 p-2.5 rounded-xl border border-zinc-900/60">
            <span className="text-xs text-zinc-400 font-medium">Evaluation Depth</span>
            <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
              depth === 'Strong' ? 'bg-purple-950/30 text-purple-400 border border-purple-500/10' : 'bg-zinc-850 text-zinc-400'
            }`}>{depth}</span>
          </div>
          <div className="flex justify-between items-center bg-zinc-950/40 p-2.5 rounded-xl border border-zinc-900/60">
            <span className="text-xs text-zinc-400 font-medium">Clarity Score</span>
            <span className="text-xs font-bold font-mono text-zinc-200">{clarityScore !== null ? `${clarityScore}%` : 'Waiting...'}</span>
          </div>
        </div>
      </div>

      {/* ── Real-Time Evaluation Feedback ── */}
      <AnimatePresence mode="wait">
        {accuracy !== null ? (
          <motion.div 
            key={questionCount}
            variants={listVariants}
            initial="hidden"
            animate="show"
            exit="hidden"
            className="space-y-5"
          >
            {/* Strengths List (Green) */}
            {strengths.length > 0 && (
              <motion.div variants={itemVariants} className="glass-card p-4.5 rounded-xl border-emerald-500/10 shadow-[0_0_15px_rgba(16,185,129,0.02)]">
                <span className="text-[10px] text-emerald-400 font-bold tracking-wider uppercase block mb-3 flex items-center gap-1.5">
                  <Award size={12} className="text-emerald-400" /> Live Strengths
                </span>
                <div className="space-y-2">
                  {strengths.map((str, idx) => (
                    <div key={idx} className="flex gap-2 text-xs text-zinc-300 items-start leading-relaxed pl-0.5">
                      <ChevronRight size={13} className="text-emerald-500 shrink-0 mt-0.5" />
                      <span>{str}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Gaps List (Red) */}
            {gaps.length > 0 && (
              <motion.div variants={itemVariants} className="glass-card p-4.5 rounded-xl border-red-500/10 shadow-[0_0_15px_rgba(239,68,68,0.02)]">
                <span className="text-[10px] text-red-400 font-bold tracking-wider uppercase block mb-3 flex items-center gap-1.5">
                  <ShieldAlert size={12} className="text-red-400" /> Knowledge Gaps
                </span>
                <div className="space-y-2">
                  {gaps.map((gap, idx) => (
                    <div key={idx} className="flex gap-2 text-xs text-zinc-300 items-start leading-relaxed pl-0.5">
                      <ChevronRight size={13} className="text-red-400 shrink-0 mt-0.5" />
                      <span>{gap}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Suggestions List (Blue) */}
            {suggestions.length > 0 && (
              <motion.div variants={itemVariants} className="glass-card p-4.5 rounded-xl border-blue-500/10 shadow-[0_0_15px_rgba(59,130,246,0.02)]">
                <span className="text-[10px] text-blue-400 font-bold tracking-wider uppercase block mb-3 flex items-center gap-1.5">
                  <Sparkles size={12} className="text-blue-400 animate-pulse" /> Focus Suggestions
                </span>
                <div className="space-y-2">
                  {suggestions.map((sug, idx) => (
                    <div key={idx} className="flex gap-2 text-xs text-zinc-300 items-start leading-relaxed pl-0.5">
                      <ChevronRight size={13} className="text-blue-400 shrink-0 mt-0.5" />
                      <span>{sug}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </motion.div>
        ) : (
          <div className="flex-1 border border-dashed border-zinc-800/80 rounded-2xl flex flex-col items-center justify-center p-6 text-center text-zinc-650 gap-2">
            <Activity className="animate-pulse text-zinc-700" size={24} />
            <p className="text-[11px] font-sans font-medium tracking-tight text-zinc-500">Waiting for response evaluation...</p>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
