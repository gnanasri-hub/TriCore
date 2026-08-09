import React from 'react';
import { motion } from 'framer-motion';
import { Award, AlertTriangle, Play, RefreshCw, CheckCircle2, ChevronRight } from 'lucide-react';

export default function FeedbackScreen({ feedback, onReset }) {
  const { summary, strengths = [], gaps = [], next = [] } = feedback || {};

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { type: "spring", stiffness: 120, damping: 14 }
    }
  };

  const badgeVariants = {
    hidden: { scale: 0.8, opacity: 0 },
    visible: { 
      scale: 1, 
      opacity: 1,
      transition: { type: "spring", stiffness: 200, damping: 10 }
    }
  };

  return (
    <motion.div 
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full max-w-4xl mx-auto py-8 px-4"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center mb-10">
        <div className="inline-flex p-3 rounded-2xl bg-purple-500/10 border border-purple-500/30 text-purple-400 mb-4 shadow-[0_0_20px_rgba(168,85,247,0.15)]">
          <Award size={36} />
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight font-display bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 mb-2">
          Interview Complete
        </h1>
        <p className="text-zinc-400 text-base max-w-lg mx-auto">
          Here is a detailed, AI-generated assessment of your technical depth, strengths, and recommended focus areas.
        </p>
      </motion.div>

      {/* Main assessment grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        
        {/* Left Side: Summary & Strengths */}
        <div className="space-y-8">
          {/* Summary Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-2xl border-purple-500/10">
            <h2 className="text-lg font-bold text-zinc-100 font-display mb-3 flex items-center gap-2">
              <CheckCircle2 className="text-purple-400" size={20} />
              Evaluation Summary
            </h2>
            <p className="text-zinc-300 text-[14px] leading-relaxed italic border-l-2 border-purple-500/50 pl-3">
              "{summary || 'Your performance review is ready.'}"
            </p>
          </motion.div>

          {/* Strengths Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-2xl border-emerald-500/10 shadow-[0_0_25px_rgba(16,185,129,0.02)]">
            <h2 className="text-lg font-bold text-zinc-100 font-display mb-4 flex items-center gap-2">
              <Award className="text-emerald-400" size={20} />
              Key Strengths
            </h2>
            <div className="space-y-3">
              {strengths.map((str, idx) => (
                <motion.div 
                  key={idx}
                  variants={badgeVariants}
                  className="flex items-start gap-3 bg-emerald-950/20 border border-emerald-500/15 p-3 rounded-xl"
                >
                  <span className="text-[12px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-md font-bold mt-0.5 shrink-0">
                    S{idx + 1}
                  </span>
                  <p className="text-zinc-300 text-[13px] leading-relaxed">{str}</p>
                </motion.div>
              ))}
              {strengths.length === 0 && (
                <p className="text-zinc-500 text-xs italic">No specific strengths recorded.</p>
              )}
            </div>
          </motion.div>
        </div>

        {/* Right Side: Gaps & Next Steps */}
        <div className="space-y-8">
          {/* Gaps Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-2xl border-amber-500/10 shadow-[0_0_25px_rgba(245,158,11,0.02)]">
            <h2 className="text-lg font-bold text-zinc-100 font-display mb-4 flex items-center gap-2">
              <AlertTriangle className="text-amber-400" size={20} />
              Identified Gaps
            </h2>
            <div className="space-y-3">
              {gaps.map((gap, idx) => (
                <motion.div 
                  key={idx}
                  variants={badgeVariants}
                  className="flex items-start gap-3 bg-amber-950/20 border border-amber-500/15 p-3 rounded-xl"
                >
                  <span className="text-[12px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-md font-bold mt-0.5 shrink-0">
                    G{idx + 1}
                  </span>
                  <p className="text-zinc-300 text-[13px] leading-relaxed">{gap}</p>
                </motion.div>
              ))}
              {gaps.length === 0 && (
                <p className="text-zinc-500 text-xs italic">No significant gaps identified.</p>
              )}
            </div>
          </motion.div>

          {/* Next Steps Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-2xl border-blue-500/10 shadow-[0_0_25px_rgba(59,130,246,0.02)]">
            <h2 className="text-lg font-bold text-zinc-100 font-display mb-4 flex items-center gap-2">
              <Play className="text-blue-400 rotate-90" size={20} />
              Recommended Next Steps
            </h2>
            <div className="space-y-3">
              {next.map((step, idx) => (
                <motion.div 
                  key={idx}
                  variants={badgeVariants}
                  className="flex items-start gap-3 bg-blue-950/20 border border-blue-500/15 p-3 rounded-xl"
                >
                  <ChevronRight className="text-blue-400 shrink-0 mt-0.5" size={16} />
                  <p className="text-zinc-300 text-[13px] leading-relaxed">{step}</p>
                </motion.div>
              ))}
              {next.length === 0 && (
                <p className="text-zinc-500 text-xs italic">No specific next steps provided.</p>
              )}
            </div>
          </motion.div>
        </div>

      </div>

      {/* Action Footer */}
      <motion.div variants={itemVariants} className="flex justify-center pt-4">
        <motion.button
          onClick={onReset}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="flex items-center gap-2 px-6 py-3.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-semibold rounded-xl cursor-pointer glow-btn-purple transition-all duration-300"
        >
          <RefreshCw size={18} />
          Start New Simulator Session
        </motion.button>
      </motion.div>
    </motion.div>
  );
}
