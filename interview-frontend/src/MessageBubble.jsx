import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, Zap, Maximize2, X, AlertCircle, CheckCircle2, ChevronRight, Activity, ArrowUpRight } from 'lucide-react';

const getRecommendationTip = (gapText) => {
  if (!gapText) return '';
  const text = gapText.toLowerCase();
  if (text.includes("sql") || text.includes("database")) {
    return "Study transaction isolations and query optimize patterns.";
  }
  if (text.includes("rag") || text.includes("vector")) {
    return "Check chunk boundaries and study dense vs sparse vector search models.";
  }
  if (text.includes("agent") || text.includes("mcp")) {
    return "Review state orchestrations and Model Context Protocol schema definitions.";
  }
  if (text.includes("cache") || text.includes("redis")) {
    return "Study cache eviction keys and Redis serialization protocols.";
  }
  if (text.includes("api") || text.includes("fastapi")) {
    return "Define responses using explicit Pydantic schemas.";
  }
  return "Deepen understanding of core topic objective boundaries.";
};

export default function MessageBubble({ message }) {
  const isBot = message.role === 'assistant';
  const [isExpanded, setIsExpanded] = useState(false);

  const isLong = isBot && message.content && message.content.length > 280;
  const [isClamped, setIsClamped] = useState(isLong);

  const renderFormattedContent = (text) => {
    if (!text) return '';
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-extrabold text-white bg-purple-500/10 px-1 py-0.5 rounded border border-purple-500/20">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  const bubbleVariants = {
    hidden: { opacity: 0, x: isBot ? -24 : 24, y: 8, scale: 0.98 },
    visible: { 
      opacity: 1, 
      x: 0,
      y: 0, 
      scale: 1,
      transition: { 
        type: "spring", 
        stiffness: 240, 
        damping: 18,
        mass: 0.9
      }
    }
  };

  return (
    <>
      <motion.div
        variants={bubbleVariants}
        initial="hidden"
        animate="visible"
        className={`flex items-start gap-4 mb-6 w-full ${isBot ? 'self-start max-w-3xl' : 'self-end max-w-2xl flex-row-reverse'}`}
      >
        {/* Avatar */}
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border transition-all duration-300 ${
          isBot 
            ? 'bg-purple-950/40 border-purple-500/25 text-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.15)]' 
            : 'bg-zinc-800 border-zinc-700 text-zinc-300'
        }`}>
          {isBot ? <Bot size={18} /> : <User size={18} />}
        </div>

        {/* Bubble Container */}
        <div className="flex-1 flex flex-col gap-1.5 min-w-0">
          <div className={`flex items-center gap-2 px-1 ${isBot ? 'self-start' : 'self-end flex-row-reverse'}`}>
            <span className="text-[10px] font-bold tracking-widest uppercase opacity-35 select-none">
              {isBot ? 'AI Agent' : 'You'}
            </span>
          </div>

          {/* Message bubble - Auto-sizing, max-w-3xl, whitespace-pre-wrap, leading-8, larger text */}
          <div className={`group p-5.5 rounded-2xl leading-8 text-[17px] font-sans relative transition-all duration-300 h-auto min-h-[48px] ${
            isBot 
              ? 'glass-card border-purple-500/10 text-zinc-100 rounded-tl-none shadow-[0_4px_25px_rgba(168,85,247,0.02)] hover:border-purple-500/20' 
              : 'bg-zinc-900 border border-zinc-800/80 text-zinc-100 rounded-tr-none hover:border-zinc-700/50'
          } ${isClamped ? 'max-h-[170px] overflow-hidden' : ''}`}>
            
            {message.isFollowUp && isBot && (
              <div className="absolute -top-3.5 left-3 bg-gradient-to-r from-purple-600 to-pink-650 text-[9px] uppercase font-extrabold tracking-widest text-white px-2.5 py-1 rounded-full flex items-center gap-1 border border-purple-400/20 shadow-[0_0_15px_rgba(168,85,247,0.3)] z-10">
                <Zap size={10} className="fill-white animate-pulse" />
                ⚡ AI is probing deeper
              </div>
            )}

            {isBot && message.content && (
              <div className="flex gap-2 mb-3.5 select-none">
                <span className="text-[10px] font-mono font-bold bg-blue-950/40 text-blue-400 px-2 py-0.5 rounded border border-blue-500/15 uppercase tracking-wide">
                  {message.domain || "AI Engineering"}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase tracking-wide ${
                  message.difficulty === 'Hard' 
                    ? 'bg-pink-955/35 text-pink-400 border-pink-500/15' 
                    : 'bg-purple-955/35 text-purple-400 border-purple-500/15'
                }`}>
                  {message.difficulty || "Standard"}
                </span>
              </div>
            )}
            
            {/* Main content - whitespace-pre-wrap */}
            <p className="whitespace-pre-wrap text-zinc-200 pr-4">
              {renderFormattedContent(message.content)}
              {isBot && message.content && message.content.length > 0 && !message.content.endsWith('?') && (
                <span className="animate-pulse bg-purple-500 w-1.5 h-4 ml-1 inline-block select-none font-bold">▋</span>
              )}
            </p>

            {/* Expand modal trigger button */}
            {isBot && message.content && !isClamped && (
              <button 
                onClick={() => setIsExpanded(true)}
                className="absolute right-3.5 bottom-3.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 p-1.5 bg-zinc-950/80 border border-zinc-850 hover:border-purple-500/40 text-zinc-400 hover:text-purple-400 rounded-lg cursor-pointer"
                title="Expand Reading Mode"
              >
                <Maximize2 size={13} />
              </button>
            )}

            {/* Long message clamp fade out overlay */}
            {isClamped && (
              <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#0d0d12] via-[#0d0d12]/90 to-transparent flex items-end justify-center pb-3">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsClamped(false);
                  }}
                  className="text-purple-400 hover:text-purple-300 font-bold text-[11px] uppercase tracking-wider flex items-center gap-1 cursor-pointer bg-zinc-900 px-3.5 py-1.5 rounded-full border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.3)] transition-all hover:scale-105"
                >
                  Continue reading ↓
                </button>
              </div>
            )}

            {/* Real-time evaluation breakdown */}
            {isBot && message.evaluation && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="mt-5 pt-4 border-t border-zinc-900 flex flex-col gap-3.5"
              >
                <div className="flex items-center gap-1.5 text-[9px] text-zinc-500 font-extrabold uppercase tracking-widest">
                  <Activity size={12} className="text-purple-400" />
                  Response Evaluation Matrix
                </div>
                <div className="grid grid-cols-1 gap-2 text-xs font-sans">
                  {message.evaluation.strengths?.[0] && (
                    <div className="flex gap-2 items-start text-emerald-400 bg-emerald-950/20 border border-emerald-500/10 px-3.5 py-2.5 rounded-xl">
                      <CheckCircle2 size={14} className="shrink-0 text-emerald-400 mt-0.5" />
                      <div>
                        <span className="font-extrabold block text-[10px] uppercase tracking-wider text-emerald-500 mb-0.5">Strength Detected</span>
                        <span className="text-zinc-300 leading-relaxed">{message.evaluation.strengths[0]}</span>
                      </div>
                    </div>
                  )}
                  {message.evaluation.missing_points?.[0] && (
                    <div className="flex gap-2 items-start text-red-400 bg-red-950/20 border border-red-500/10 px-3.5 py-2.5 rounded-xl">
                      <AlertCircle size={14} className="shrink-0 text-red-400 mt-0.5" />
                      <div>
                        <span className="font-extrabold block text-[10px] uppercase tracking-wider text-red-500 mb-0.5">Knowledge Gap</span>
                        <span className="text-zinc-300 leading-relaxed">{message.evaluation.missing_points[0]}</span>
                      </div>
                    </div>
                  )}
                  {message.evaluation.missing_points?.[0] && (
                    <div className="flex gap-2 items-start text-blue-400 bg-blue-950/20 border border-blue-500/10 px-3.5 py-2.5 rounded-xl">
                      <ArrowUpRight size={14} className="shrink-0 text-blue-400 mt-0.5" />
                      <div>
                        <span className="font-extrabold block text-[10px] uppercase tracking-wider text-blue-400 mb-0.5">Calibration Suggestion</span>
                        <span className="text-zinc-300 leading-relaxed">{getRecommendationTip(message.evaluation.missing_points[0])}</span>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Reader Mode Expand Modal */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4"
          >
            <motion.div 
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              className="glass-card max-w-[800px] w-full rounded-3xl p-8 relative border-purple-500/20 shadow-[0_0_50px_rgba(168,85,247,0.1)]"
            >
              {/* Close Button */}
              <button 
                onClick={() => setIsExpanded(false)}
                className="absolute top-6 right-6 p-2 bg-zinc-900 border border-zinc-800 hover:border-red-500/40 text-zinc-400 hover:text-red-400 rounded-xl cursor-pointer transition-colors duration-250"
              >
                <X size={18} />
              </button>

              <div className="flex items-center gap-2 text-purple-400 mb-6 font-display font-bold text-xs uppercase tracking-widest">
                <Bot size={16} />
                Focused Question Reader
              </div>

              {/* Large readable text layout */}
              <div className="text-zinc-100 text-xl font-medium font-sans leading-loose select-text pr-4 max-h-[60vh] overflow-y-auto">
                <p className="whitespace-pre-wrap text-zinc-250">
                  {renderFormattedContent(message.content)}
                </p>
              </div>

              <div className="mt-8 pt-4 border-t border-zinc-900 flex justify-between items-center text-xs text-zinc-500 font-mono">
                <span>AI Interview Agent Assessment</span>
                <span className="flex items-center gap-1">
                  <AlertCircle size={12} /> Use this mode for complex technical scenario questions
                </span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
