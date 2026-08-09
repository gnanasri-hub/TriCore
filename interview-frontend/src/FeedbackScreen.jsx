import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Award, AlertTriangle, Play, RefreshCw, CheckCircle2, ChevronRight, Activity } from 'lucide-react';

export default function FeedbackScreen({ feedback, onReset }) {
  const { summary, strengths = [], gaps = [], next = [] } = feedback || {};
  const [score, setScore] = useState(0);

  const calculatedScore = Math.max(50, Math.min(95, Math.floor(
    70 + (strengths.length * 5) - (gaps.length * 4)
  )));

  useEffect(() => {
    let start = 0;
    const end = calculatedScore;
    if (start === end) return;
    const totalDuration = 1500;
    const incrementTime = Math.abs(Math.floor(totalDuration / end));
    
    const timer = setInterval(() => {
      start += 1;
      setScore(start);
      if (start >= end) {
        clearInterval(timer);
      }
    }, incrementTime);

    return () => clearInterval(timer);
  }, [calculatedScore]);

  // Skill axes coordinates for the SVG Radar chart
  const axes = [
    { name: "System Design", angle: 0, val: 0.85 },
    { name: "RAG & Vector", angle: 72, val: 0.90 },
    { name: "Agents", angle: 144, val: 0.70 },
    { name: "Deployment", angle: 216, val: 0.65 },
    { name: "Observability", angle: 288, val: 0.50 }
  ];

  const getCoordinates = (angle, value) => {
    const rad = (angle - 90) * (Math.PI / 180);
    const radius = 70 * value;
    const x = 100 + radius * Math.cos(rad);
    const y = 100 + radius * Math.sin(rad);
    return { x, y };
  };

  const points = axes.map(axis => {
    const coords = getCoordinates(axis.angle, axis.val);
    return `${coords.x},${coords.y}`;
  }).join(' ');

  const outerWebPoints = [1, 0.75, 0.5, 0.25].map(scale => {
    return axes.map(axis => {
      const coords = getCoordinates(axis.angle, scale);
      return `${coords.x},${coords.y}`;
    }).join(' ') + ' ' + getCoordinates(axes[0].angle, scale).x + ',' + getCoordinates(axes[0].angle, scale).y;
  });

  // Staggered variants for sequential entry
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1, 
      transition: { staggerChildren: 0.12, delayChildren: 0.1 } 
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 25 },
    visible: { 
      opacity: 1, 
      y: 0, 
      transition: { type: "spring", stiffness: 140, damping: 15 } 
    }
  };

  const badgeVariants = {
    hidden: { scale: 0.9, opacity: 0 },
    visible: { 
      scale: 1, 
      opacity: 1, 
      transition: { type: "spring", stiffness: 200, damping: 12 } 
    }
  };

  return (
    <motion.div 
      variants={containerVariants} 
      initial="hidden" 
      animate="visible" 
      className="w-full max-w-5xl mx-auto py-8 px-4"
    >
      {/* Header section */}
      <motion.div variants={itemVariants} className="text-center mb-10">
        <div className="inline-flex p-3 rounded-2xl bg-purple-500/10 border border-purple-500/30 text-purple-400 mb-4 shadow-[0_0_20px_rgba(168,85,247,0.15)]">
          <Award size={36} />
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight font-display bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 mb-2">
          Technical Evaluation Complete
        </h1>
        <p className="text-zinc-400 text-sm max-w-lg mx-auto">
          Comprehensive, adaptive grading report evaluating core AI Engineering competencies.
        </p>
      </motion.div>

      {/* Main panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Left Side: Score & Radar Skill Graph */}
        <motion.div 
          variants={itemVariants} 
          className="lg:col-span-1 glass-card p-6 rounded-3xl border-purple-500/10 flex flex-col items-center justify-center relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-purple-500 to-pink-500" />
          <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-extrabold mb-6">Cognitive Skill Index</span>

          {/* Animated score meter */}
          <div className="relative w-40 h-40 flex items-center justify-center mb-6">
            <svg className="absolute w-full h-full transform -rotate-90">
              <circle cx="80" cy="80" r="70" className="stroke-zinc-950 fill-none stroke-[8]" />
              <motion.circle 
                cx="80" 
                cy="80" 
                r="70" 
                className="stroke-purple-600 fill-none stroke-[8] stroke-linecap-round" 
                initial={{ strokeDasharray: "440 440", strokeDashoffset: 440 }} 
                animate={{ strokeDashoffset: 440 - (440 * score) / 100 }} 
                transition={{ duration: 1.5, ease: "easeOut" }} 
              />
            </svg>
            <div className="flex flex-col items-center">
              <span className="text-5xl font-extrabold text-white tracking-tighter font-display">{score}</span>
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest mt-1">Total Index</span>
            </div>
          </div>

          {/* SVG Radar Visualization with soft glow */}
          <div className="w-52 h-52 relative">
            <svg viewBox="0 0 200 200" className="w-full h-full overflow-visible">
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Web ring dividers */}
              {outerWebPoints.map((pts, i) => (
                <polygon key={i} points={pts} className="fill-none stroke-zinc-900 stroke-[1]" />
              ))}
              
              {/* Axes lines */}
              {axes.map((axis, i) => {
                const target = getCoordinates(axis.angle, 1);
                return <line key={i} x1="100" y1="100" x2={target.x} x2={target.x} y2={target.y} className="stroke-zinc-900 stroke-[1]" />;
              })}

              {/* Skill Area Polygon with glow filter */}
              <polygon 
                points={points} 
                filter="url(#glow)"
                className="fill-purple-500/15 stroke-purple-500 stroke-[1.5] shadow-lg" 
              />

              {/* Data points */}
              {axes.map((axis, i) => {
                const coords = getCoordinates(axis.angle, axis.val);
                return <circle key={i} cx={coords.x} cy={coords.y} r="3.5" className="fill-pink-500 stroke-zinc-950 stroke-[1]" />;
              })}

              {/* Labels */}
              {axes.map((axis, i) => {
                const coords = getCoordinates(axis.angle, 1.25);
                return <text key={i} x={coords.x} y={coords.y} textAnchor="middle" dominantBaseline="middle" className="fill-zinc-500 font-mono text-[8px] font-bold uppercase tracking-wider">{axis.name}</text>;
              })}
            </svg>
          </div>
        </motion.div>

        {/* Right Side: Evaluation summary, strengths, and weaknesses */}
        <div className="lg:col-span-2 space-y-6 flex flex-col justify-between">
          {/* Summary Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-3xl border-purple-500/10">
            <h2 className="text-sm font-bold text-zinc-300 font-display mb-3 uppercase tracking-wider flex items-center gap-2">
              <Activity className="text-purple-400" size={16} /> Evaluation Summary
            </h2>
            <p className="text-zinc-350 text-[14.5px] leading-relaxed italic border-l-2 border-purple-500/50 pl-3.5">
              "{summary || 'Evaluation summary generated successfully.'}"
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Strengths Card */}
            <motion.div variants={itemVariants} className="glass-card p-5 rounded-2xl border-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.01)]">
              <h2 className="text-xs font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="text-emerald-400" size={16} /> Demonstrated Strengths
              </h2>
              <div className="space-y-2.5">
                {strengths.map((str, idx) => (
                  <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-2.5 bg-emerald-950/20 border border-emerald-500/10 p-3 rounded-xl">
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono font-bold mt-0.5 shrink-0">S{idx + 1}</span>
                    <p className="text-zinc-350 text-xs leading-relaxed">{str}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Weaknesses Card */}
            <motion.div variants={itemVariants} className="glass-card p-5 rounded-2xl border-red-500/10 shadow-[0_0_20px_rgba(239,68,68,0.01)]">
              <h2 className="text-xs font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="text-red-400" size={16} /> Identified Weaknesses / Gaps
              </h2>
              <div className="space-y-2.5">
                {gaps.map((gap, idx) => (
                  <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-2.5 bg-red-950/20 border border-red-500/10 p-3 rounded-xl">
                    <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-mono font-bold mt-0.5 shrink-0">W{idx + 1}</span>
                    <p className="text-zinc-350 text-xs leading-relaxed">{gap}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Suggested Learning Path */}
      <motion.div variants={itemVariants} className="glass-card p-6 rounded-3xl border-blue-500/10 shadow-[0_0_30px_rgba(59,130,246,0.02)] mb-8">
        <h2 className="text-sm font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
          <Play className="text-blue-400 rotate-90" size={16} /> Suggested Learning Path & Next Steps
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {next.map((step, idx) => (
            <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-3 bg-blue-950/20 border border-blue-500/10 p-4 rounded-2xl">
              <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400 text-xs font-mono font-bold shrink-0 mt-0.5">{idx + 1}</div>
              <p className="text-zinc-350 text-xs leading-relaxed">{step}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Action triggers */}
      <motion.div variants={itemVariants} className="flex justify-center pt-4">
        <motion.button onClick={onReset} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 px-6 py-3.5 bg-gradient-to-r from-purple-600 to-pink-650 text-white font-semibold rounded-xl cursor-pointer glow-btn-purple transition-all duration-300">
          <RefreshCw size={18} /> Start New Simulator Session
        </motion.button>
      </motion.div>
    </motion.div>
  );
}
