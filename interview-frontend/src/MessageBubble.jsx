import React from 'react';
import { motion } from 'framer-motion';
import { Bot, User, CornerDownRight } from 'lucide-react';

export default function MessageBubble({ message, isLast }) {
  const isBot = message.role === 'assistant';

  const containerVariants = {
    hidden: { opacity: 0, y: 15, scale: 0.98 },
    visible: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { 
        type: "spring",
        stiffness: 260,
        damping: 20,
        duration: 0.4
      }
    }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={`flex items-start gap-4 mb-6 max-w-[85%] ${isBot ? 'self-start' : 'self-end flex-row-reverse'}`}
    >
      {/* Avatar */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${
        isBot 
          ? 'bg-purple-950/40 border-purple-500/30 text-purple-400 glow-btn-purple' 
          : 'bg-zinc-800 border-zinc-700 text-zinc-300'
      }`}>
        {isBot ? <Bot size={18} /> : <User size={18} />}
      </div>

      {/* Bubble Container */}
      <div className="flex flex-col gap-1">
        {/* Role label */}
        <span className={`text-[11px] font-medium tracking-wider uppercase opacity-40 px-1 ${
          isBot ? 'self-start' : 'self-end'
        }`}>
          {isBot ? 'AI Agent' : 'You'}
        </span>

        {/* Message bubble */}
        <div className={`p-4 rounded-2xl leading-relaxed text-[15px] font-sans relative ${
          isBot 
            ? 'glass-card border-purple-500/10 text-zinc-100 rounded-tl-none shadow-[0_0_15px_rgba(168,85,247,0.03)]' 
            : 'bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tr-none'
        }`}>
          {message.isFollowUp && isBot && (
            <div className="absolute -top-3 left-3 bg-purple-600/90 text-[10px] uppercase font-bold tracking-widest text-white px-2 py-0.5 rounded-full flex items-center gap-1 border border-purple-400/30 shadow-[0_0_10px_rgba(168,85,247,0.4)]">
              <CornerDownRight size={10} />
              Follow-up Question
            </div>
          )}
          <p className="whitespace-pre-line">{message.content}</p>
        </div>
      </div>
    </motion.div>
  );
}
