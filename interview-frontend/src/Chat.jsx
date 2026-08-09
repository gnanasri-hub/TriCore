import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MessageBubble from './MessageBubble';
import { Loader2, Sparkles, BookOpen, Layers } from 'lucide-react';

const TOPICS = {
  1: "Python & Git Basics",
  2: "FastAPI Development",
  3: "SQL Databases",
  4: "NoSQL Stores",
  5: "Redis Caching",
  6: "LLM APIs Intro",
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

export default function Chat({ messages, isThinking, progress, sessionStatus }) {
  const scrollRef = useRef(null);
  
  const questionCount = sessionStatus?.question_count || 1;
  const coveredDays = sessionStatus?.covered_days || [];
  const currentStage = sessionStatus?.interview_stage || "INTERVIEWING";
  const isPendingFollowUp = sessionStatus?.pending_follow_up?.is_pending || false;

  // Auto-scroll logic
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isThinking]);

  // Calculate progress percentage
  const progressPercent = Math.min((questionCount / 8) * 100, 100);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden w-full max-w-[800px] mx-auto px-4">
      {/* Top Header Card: Progress & Covered Topics */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-4 rounded-2xl border-purple-500/10 mb-6 flex flex-col gap-3 relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 h-[2px] bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 w-full" />
        
        {/* Progress Bar Header */}
        <div className="flex justify-between items-center text-xs">
          <div className="flex items-center gap-2 text-zinc-300">
            <Sparkles size={14} className="text-purple-400 animate-pulse" />
            <span className="font-semibold">Technical Validation Stage</span>
          </div>
          <span className="text-purple-400 font-mono font-bold">
            Question {questionCount} of 8+
          </span>
        </div>

        {/* Progress Bar Line */}
        <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800/50">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"
          />
        </div>

        {/* Covered Days Chips */}
        {coveredDays.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-1 border-t border-zinc-800/40 pt-3">
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold mr-1 flex items-center gap-1">
              <Layers size={10} />
              Domains Probed:
            </span>
            <AnimatePresence>
              {coveredDays.map((dayNum) => (
                <motion.span
                  key={dayNum}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="text-[11px] font-medium bg-purple-950/20 border border-purple-500/20 text-purple-300 px-2 py-0.5 rounded-md flex items-center gap-1"
                >
                  <BookOpen size={10} className="opacity-70" />
                  {TOPICS[dayNum] || `Day ${dayNum}`}
                </motion.span>
              ))}
            </AnimatePresence>
          </div>
        )}
      </motion.div>

      {/* Message Scroll Container */}
      <div className="flex-1 overflow-y-auto px-1 py-4 space-y-4 rounded-2xl">
        <div className="flex flex-col min-h-full justify-end">
          {messages.map((msg, index) => (
            <MessageBubble 
              key={msg.id || index} 
              message={msg} 
              isLast={index === messages.length - 1} 
            />
          ))}

          {/* Thinking State */}
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
                <div className="p-4 rounded-2xl glass-card border-purple-500/10 text-zinc-400 rounded-tl-none flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-xs font-medium animate-pulse text-zinc-500">
                    AI is analyzing your answer...
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={scrollRef} />
        </div>
      </div>
    </div>
  );
}
