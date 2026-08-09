import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { SendHorizontal } from 'lucide-react';

export default function InputBox({ onSendMessage, disabled, placeholder, onStartTyping }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim());
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
      <div className="relative flex items-center glass-card border-zinc-800 rounded-2xl overflow-hidden focus-within:border-purple-500/40 focus-within:ring-2 focus-within:ring-purple-500/15 transition-all duration-300 shadow-[0_0_20px_rgba(168,85,247,0.05)] px-2 py-1.5 gap-2">
        <textarea
          ref={inputRef}
          rows={1}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (onStartTyping) onStartTyping();
          }}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Waiting for AI..." : placeholder || "Type your answer..."}
          disabled={disabled}
          className="flex-1 max-h-32 bg-transparent text-[15px] font-sans text-zinc-100 placeholder-zinc-500 px-3 py-2.5 outline-none resize-none disabled:cursor-not-allowed leading-relaxed"
        />
        
        <motion.button
          type="submit"
          disabled={!text.trim() || disabled}
          whileHover={{ scale: 1.08, boxShadow: "0 0 15px rgba(168, 85, 247, 0.4)" }}
          whileTap={{ scale: 0.92 }}
          className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 shrink-0 cursor-pointer ${
            text.trim() && !disabled
              ? 'bg-purple-600 hover:bg-purple-500 text-white glow-btn-purple'
              : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
          }`}
        >
          <SendHorizontal size={18} />
        </motion.button>
      </div>
      <div className="flex justify-between items-center px-4 mt-2">
        <p className="text-[10px] text-zinc-500 select-none">
          Press <kbd className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[9px]">Enter</kbd> to submit, <kbd className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[9px]">Shift+Enter</kbd> for new line
        </p>
      </div>
    </form>
  );
}
