import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MessageBubble from './MessageBubble';
import { Loader2, Sparkles, BookOpen, Layers, Keyboard } from 'lucide-react';

const TOPICS = {
  7: "Embeddings",
  8: "Vector Databases",
  9: "Semantic Search",
  10: "Retrieval Engines",
  11: "RAG End-to-End",
  12: "Prompt Engineering",
  13: "Agent Frameworks",
  14: "Agent Tooling",
  15: "LangChain Basics",
  16: "Chatbot Backend",
  17: "Conversation History",
  18: "Token Management",
  19: "Text Summarisation",
  20: "Memory & Context",
  21: "LangChain Agents",
  22: "Multi-Agent Systems",
  23: "Model Context Protocol",
  24: "Agent Planning",
  25: "Evaluation Frameworks",
  26: "LLM Finetuning",
  27: "LoRA & QLoRA",
  28: "Docker & K8s",
  29: "Monitoring & Observability",
  30: "CI/CD for AI Apps",
  31: "Capstone Project",
};

export default function Chat({ messages, isThinking, sessionStatus, isFocusMode, setIsFocusMode, detectedDays = [] }) {
  const scrollRef = useRef(null);
  
  const questionCount = sessionStatus?.question_count || 1;
  const coveredDays = sessionStatus?.covered_days || [];
  const allCoveredDays = Array.from(new Set([...coveredDays, ...detectedDays]));

  useEffect(() => {
    if (!isFocusMode) {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isThinking, isFocusMode]);

  const progressPercent = Math.min((questionCount / 8) * 100, 100);

  const listVariants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const chipVariants = {
    hidden: { opacity: 0, y: 8, scale: 0.95 },
    show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 220, damping: 15 } }
  };

  const lastMsg = messages[messages.length - 1];
  const showFocusOverlay = isFocusMode && lastMsg && lastMsg.role === 'assistant' && !isThinking;

  const renderFormattedContent = (text) => {
    if (!text) return '';
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-extrabold text-white bg-purple-500/10 px-1 py-0.5 rounded border border-purple-500/20">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden w-full max-w-[800px] mx-auto px-4 relative mt-1 min-h-[500px]">
      
      {/* Top Header Card: Smart Adaptive Progress (PADDING REDUCED & COMPACT LAYOUT) */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-3.5 rounded-xl border-purple-500/10 mb-4 flex flex-col gap-2.5 relative overflow-hidden z-10"
      >
        <div className="absolute top-0 left-0 h-[1.5px] bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 w-full" />
        
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-1.5 text-zinc-300">
            <Sparkles size={12} className="text-purple-400 animate-pulse shrink-0" />
            <span className="font-bold text-xs tracking-tight font-display">Adaptive Progress</span>
            <span className="text-[10px] text-zinc-550 hidden sm:inline">• dynamic scaling</span>
          </div>
          <span className="text-purple-400 font-mono font-extrabold text-[9px] bg-purple-950/20 px-1.5 py-0.5 rounded border border-purple-500/10 animate-pulse">
            Q{questionCount} / 8+
          </span>
        </div>

        {/* Progress Bar (THINNER) */}
        <div className="w-full h-1 bg-zinc-950 rounded-full overflow-hidden border border-zinc-900/60 relative">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
            className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 rounded-full relative shadow-[0_0_10px_rgba(168,85,247,0.4)]"
          >
            <div className="absolute top-0 right-0 bottom-0 left-0 bg-white/20 animate-pulse" />
          </motion.div>
        </div>

        {/* Dynamic chips (COMPACT SIZES & SPACING) */}
        {allCoveredDays.length > 0 && (
          <div className="flex items-center gap-2 pt-1 border-t border-zinc-900/50 flex-wrap">
            <span className="text-[8px] text-zinc-550 uppercase tracking-widest font-extrabold shrink-0">
              Domains:
            </span>
            <motion.div 
              variants={listVariants}
              initial="hidden"
              animate="show"
              className="flex flex-wrap gap-1"
            >
              {allCoveredDays.map((dayNum) => (
                <motion.span
                  key={dayNum}
                  variants={chipVariants}
                  className="text-[9px] font-bold bg-purple-950/15 border border-purple-500/10 text-purple-300/80 px-2 py-0.5 rounded shadow-[0_1px_5px_rgba(0,0,0,0.15)] hover:border-purple-500/35 transition-all duration-150"
                >
                  {TOPICS[dayNum] || `Day ${dayNum}`}
                </motion.span>
              ))}
            </motion.div>
          </div>
        )}
      </motion.div>

      {/* Message Scroll Container */}
      <div className="flex-1 overflow-y-auto px-1 py-2 space-y-4 rounded-2xl scroll-smooth">
        <div className="flex flex-col min-h-full justify-end">
          {messages.length === 0 && !isThinking && (
            <div className="text-zinc-600 text-[10px] font-mono text-center py-12 animate-pulse uppercase tracking-widest">
              AI is preparing your first question...
            </div>
          )}

          {messages.map((msg, index) => (
            <MessageBubble 
              key={msg.id || index} 
              message={msg} 
            />
          ))}

          {/* Thinking State with Waveform reasoning bar */}
          {isThinking && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-4 mb-6 max-w-[85%] self-start"
            >
              <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-purple-950/40 border border-purple-500/20 text-purple-400 glow-btn-purple">
                <Loader2 size={18} className="animate-spin" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[11px] font-medium tracking-wider uppercase opacity-40 px-1">
                  AI Agent
                </span>
                <motion.div 
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
                  className="p-4 rounded-2xl glass-card border-purple-500/10 text-zinc-400 rounded-tl-none flex items-center gap-4.5 shadow-[0_0_15px_rgba(168,85,247,0.05)] relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
                  
                  <div className="flex items-center gap-1.5 h-4.5 shrink-0 px-1">
                    <span className="w-1 h-3.5 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full origin-bottom animate-[wave_1.2s_ease-in-out_infinite_0ms]" />
                    <span className="w-1 h-5 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full origin-bottom animate-[wave_1.2s_ease-in-out_infinite_150ms]" />
                    <span className="w-1 h-2.5 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full origin-bottom animate-[wave_1.2s_ease-in-out_infinite_300ms]" />
                    <span className="w-1 h-6 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full origin-bottom animate-[wave_1.2s_ease-in-out_infinite_450ms]" />
                    <span className="w-1 h-4 bg-gradient-to-t from-purple-500 to-pink-500 rounded-full origin-bottom animate-[wave_1.2s_ease-in-out_infinite_600ms]" />
                  </div>
                  
                  <span className="text-xs font-semibold text-zinc-400 tracking-wide select-none flex items-center gap-1.5">
                    Analyzing response
                    <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
                  </span>
                </motion.div>
              </div>
            </motion.div>
          )}

          <div ref={scrollRef} />
        </div>
      </div>

      {/* Focus Mode Question Overlay (Center-Screen Reading layout) */}
      <AnimatePresence>
        {showFocusOverlay && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center z-45 p-6 pointer-events-auto"
          >
            <motion.div 
              initial={{ scale: 0.98, opacity: 0, y: 20 }}
              animate={{ scale: 1.0, opacity: 1, y: 0 }}
              exit={{ scale: 0.98, opacity: 0, y: 20 }}
              transition={{ type: "spring", stiffness: 220, damping: 20 }}
              className="glass-card max-w-3xl w-full rounded-3xl p-8 border-purple-500/20 shadow-[0_0_60px_rgba(168,85,247,0.12)] relative"
            >
              <div className="flex justify-between items-center mb-6">
                <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 text-purple-400 px-3.5 py-1 rounded-full text-xs font-semibold tracking-wider uppercase font-display shadow-[0_0_10px_rgba(168,85,247,0.15)]">
                  <Sparkles size={12} className="animate-pulse text-purple-400" />
                  AI Question • Adaptive Evaluation
                </div>
                
                {/* Badges */}
                <div className="flex gap-2">
                  <span className="text-[10px] font-mono font-bold bg-blue-950/30 text-blue-400 px-2 py-1 rounded-lg border border-blue-500/20 uppercase">
                    {lastMsg.domain || "AI Engineering"}
                  </span>
                  <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded-lg border uppercase ${
                    lastMsg.difficulty === 'Hard' 
                      ? 'bg-pink-950/30 text-pink-400 border-pink-500/20' 
                      : 'bg-purple-950/30 text-purple-400 border-purple-500/20'
                  }`}>
                    {lastMsg.difficulty || "Standard"}
                  </span>
                </div>
              </div>

              {/* Large, relaxed line-spaced typography centered reading layout */}
              <div className="text-zinc-150 text-2xl font-medium font-sans leading-relaxed text-left max-h-[50vh] overflow-y-auto pr-2">
                <p className="whitespace-pre-wrap leading-loose text-zinc-200 pr-2">
                  {renderFormattedContent(lastMsg.content)}
                  {lastMsg.content && !lastMsg.content.endsWith('?') && (
                    <span className="animate-pulse bg-purple-500 w-1.5 h-4 ml-1 inline-block select-none font-bold">▋</span>
                  )}
                </p>
              </div>

              <div className="mt-8 pt-4 border-t border-zinc-900/60 flex items-center gap-3 text-xs text-zinc-550 font-medium font-sans">
                <Keyboard size={16} className="text-purple-400 animate-pulse" />
                <span className="animate-pulse text-zinc-450">Start typing your answer below to exit focus mode...</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
