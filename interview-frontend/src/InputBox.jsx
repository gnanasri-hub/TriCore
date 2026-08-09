import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { SendHorizontal, AlertCircle } from 'lucide-react';

const TECHNICAL_KEYWORDS = [
  'api', 'rag', 'vector', 'database', 'embed', 'prompt', 'agent', 'chain', 'model', 
  'cache', 'redis', 'sql', 'index', 'query', 'postgres', 'docker', 'kubernetes', 
  'observe', 'monitor', 'log', 'pipeline', 'python', 'framework', 'data', 'semantic', 
  'search', 'context', 'token', 'llm', 'ai', 'system', 'design', 'architecture', 'server', 'deploy'
];

export default function InputBox({ onSendMessage, disabled, placeholder, onStartTyping, lastQuestion }) {
  const [text, setText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [shake, setShake] = useState(false);
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (disabled) return;

    const trimmed = text.trim();
    if (!trimmed) return;

    // 1. Length validation (must be at least 20 characters)
    if (trimmed.length < 20) {
      setErrorMsg("Answer too short. Provide more detail.");
      setShake(true);
      setTimeout(() => setShake(false), 500);
      return;
    }

    // 2. Relevance checking
    const lowerText = trimmed.toLowerCase();
    const words = lowerText.split(/\s+/).filter(w => w.length > 2);
    
    // Check technical keyword match
    const hasTech = TECHNICAL_KEYWORDS.some(kw => lowerText.includes(kw));
    
    // Check shared terms with question context
    const questionWords = (lastQuestion || '').toLowerCase()
      .split(/\s+/)
      .map(w => w.replace(/[^\w]/g, ''))
      .filter(w => w.length > 3);
    const sharesWord = words.some(w => questionWords.includes(w));

    // Deem irrelevant if it lacks technical keywords, shares no terms, and is brief (<12 words)
    if (!hasTech && !sharesWord && words.length < 12) {
      setErrorMsg("Response does not address the question. Provide a technical explanation.");
      setShake(true);
      setTimeout(() => setShake(false), 500);
      return;
    }

    // Successful validation: clear error & submit turn
    setErrorMsg('');
    onSendMessage(trimmed);
    setText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <motion.div 
        animate={shake ? { x: [-8, 8, -6, 6, -3, 3, 0] } : {}}
        transition={{ duration: 0.4 }}
        className={`relative flex items-center glass-card rounded-2xl overflow-hidden focus-within:ring-2 focus-within:ring-purple-500/15 transition-all duration-300 shadow-[0_0_20px_rgba(168,85,247,0.05)] px-2 py-1.5 gap-2 border ${
          errorMsg 
            ? 'border-red-500/50 ring-2 ring-red-500/10' 
            : 'border-zinc-800 focus-within:border-purple-500/40'
        }`}
      >
        <textarea
          ref={inputRef}
          rows={1}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (errorMsg) setErrorMsg(''); // clear error when user types
            if (onStartTyping) onStartTyping();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Type your answer..."}
          className="flex-1 max-h-32 bg-transparent text-[15px] font-sans text-zinc-100 placeholder-zinc-550 px-3 py-2.5 outline-none resize-none leading-relaxed"
        />
        
        <motion.button
          type="submit"
          disabled={!text.trim() || disabled}
          whileHover={text.trim() && !disabled ? { scale: 1.08, boxShadow: "0 0 15px rgba(168, 85, 247, 0.4)" } : {}}
          whileTap={text.trim() && !disabled ? { scale: 0.92 } : {}}
          className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 shrink-0 cursor-pointer ${
            text.trim() && !disabled
              ? 'bg-purple-600 hover:bg-purple-500 text-white glow-btn-purple'
              : 'bg-zinc-850 text-zinc-500 cursor-not-allowed'
          }`}
        >
          <SendHorizontal size={18} />
        </motion.button>
      </motion.div>

      {/* Dynamic inline warning labels */}
      <div className="flex justify-between items-start px-2 mt-2 min-h-[20px]">
        {errorMsg ? (
          <motion.p 
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-[11px] text-red-400 flex items-center gap-1 font-semibold"
          >
            <AlertCircle size={12} className="shrink-0" />
            {errorMsg}
          </motion.p>
        ) : (
          <p className="text-[10px] text-zinc-500 select-none">
            Press <kbd className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[9px]">Enter</kbd> to submit, <kbd className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[9px]">Shift+Enter</kbd> for new line
          </p>
        )}
      </div>
    </form>
  );
}
