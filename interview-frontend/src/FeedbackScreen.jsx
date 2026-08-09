import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Award, AlertTriangle, Play, RefreshCw, CheckCircle2, ChevronRight, Activity, Zap, Compass, Star } from 'lucide-react';

// Dynamic mapper translating weaknesses into blue recommendations
const getTechnicalRecommendations = (gaps) => {
  if (!gaps || gaps.length === 0) return [
    "Explore advanced prompt engineering and multi-agent loops.",
    "Review concurrency in FastAPI routers and background tasks.",
    "Study memory structures and session handling in LangChain frameworks."
  ];
  
  return gaps.map(gap => {
    const text = gap.toLowerCase();
    if (text.includes("sql") || text.includes("database") || text.includes("postgres")) {
      return "Optimize query indexes, configure pool boundaries, and review database isolation levels.";
    }
    if (text.includes("rag") || text.includes("vector") || text.includes("embedding")) {
      return "Refine semantic overlap parameters and study hybrid dense/sparse vector search retrieval.";
    }
    if (text.includes("agent") || text.includes("langchain") || text.includes("mcp")) {
      return "Investigate Model Context Protocol capabilities and multi-agent tool execution trees.";
    }
    if (text.includes("cache") || text.includes("redis")) {
      return "Implement write-behind caching layers and study Redis cache eviction scenarios.";
    }
    if (text.includes("api") || text.includes("fastapi") || text.includes("http")) {
      return "Incorporate rigid schema serialization checks with Pydantic route response models.";
    }
    return `Review related cohort day objectives: focus on resolving core bounds in ${gap.toLowerCase()}.`;
  });
};

export default function FeedbackScreen({ feedback, onReset }) {
  const { summary, strengths = [], gaps = [], next = [] } = feedback || {};
  const [score, setScore] = useState(0);

  // Derive score index
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

  // Dynamic recommendations (Blue)
  const recommendations = getTechnicalRecommendations(gaps).slice(0, 3);

  // Radar Axes mapping exactly: Clarity, Technical Depth, Accuracy, Problem Solving
  const axes = [
    { name: "Clarity", angle: 0, val: 0.85 },
    { name: "Technical Depth", angle: 90, val: 0.78 },
    { name: "Accuracy", angle: 180, val: calculatedScore / 100 },
    { name: "Problem Solving", angle: 270, val: 0.80 }
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
      {/* ── Cinematic Hero Section ── */}
      <motion.div variants={itemVariants} className="text-center mb-12">
        <div className="inline-flex p-3 rounded-2xl bg-purple-500/10 border border-purple-500/30 text-purple-400 mb-4 shadow-[0_0_25px_rgba(168,85,247,0.2)] animate-pulse">
          <Award size={38} />
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight font-display bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 mb-2">
          Interview Complete
        </h1>
        <p className="text-zinc-400 text-sm max-w-md mx-auto">
          Technical evaluation finalized. Adaptive matrices compiled and calibrated.
        </p>
      </motion.div>

      {/* ── Main Dashboard Layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        
        {/* Left Card: Animated score counter & SVG Radar graph */}
        <motion.div 
          variants={itemVariants} 
          className="lg:col-span-1 glass-card p-6 rounded-3xl border-purple-500/15 flex flex-col items-center justify-center relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-purple-500 to-pink-500" />
          <span className="text-[10px] text-zinc-550 uppercase tracking-widest font-extrabold mb-6">Cognitive Skill Index</span>

          {/* Animated Score Progress ring */}
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
              <span className="text-[10px] text-zinc-550 uppercase font-bold tracking-widest mt-1">Total Index</span>
            </div>
          </div>

          {/* SVG Radar Skill Web */}
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
                return <line key={i} x1="100" y1="100" x2={target.x} y2={target.y} className="stroke-zinc-900 stroke-[1]" />;
              })}

              {/* Skill Area Polygon with glow filter */}
              <polygon 
                points={points} 
                filter="url(#glow)"
                className="fill-purple-500/15 stroke-purple-500 stroke-[1.5]" 
              />

              {/* Data points */}
              {axes.map((axis, i) => {
                const coords = getCoordinates(axis.angle, axis.val);
                return <circle key={i} cx={coords.x} cy={coords.y} r="3.5" className="fill-pink-500 stroke-zinc-950 stroke-[1]" />;
              })}

              {/* Labels */}
              {axes.map((axis, i) => {
                const coords = getCoordinates(axis.angle, 1.25);
                return (
                  <text 
                    key={i} 
                    x={coords.x} 
                    y={coords.y} 
                    textAnchor="middle" 
                    dominantBaseline="middle" 
                    className="fill-zinc-500 font-mono text-[8px] font-bold uppercase tracking-wider"
                  >
                    {axis.name}
                  </text>
                );
              })}
            </svg>
          </div>
        </motion.div>

        {/* Right Side: Narrative, Strengths, and Weaknesses */}
        <div className="lg:col-span-2 space-y-6 flex flex-col justify-between">
          
          {/* Summary Card */}
          <motion.div variants={itemVariants} className="glass-card p-6 rounded-3xl border-purple-500/10">
            <h2 className="text-sm font-bold text-zinc-300 font-display mb-3 uppercase tracking-wider flex items-center gap-2">
              <Activity className="text-purple-400" size={16} /> Evaluation Narrative
            </h2>
            <p className="text-zinc-350 text-[14.5px] leading-relaxed italic border-l-2 border-purple-500/50 pl-3.5">
              "{summary || 'Calibration narrative generated successfully.'}"
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Strengths Card (Green) */}
            <motion.div variants={itemVariants} className="glass-card p-5 rounded-2xl border-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.01)]">
              <h2 className="text-xs font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="text-emerald-400" size={16} /> Demonstrated Strengths
              </h2>
              <div className="space-y-2.5">
                {strengths.map((str, idx) => (
                  <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-2.5 bg-emerald-950/20 border border-emerald-500/10 p-3.5 rounded-xl">
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono font-bold mt-0.5 shrink-0">S{idx + 1}</span>
                    <p className="text-zinc-350 text-xs leading-relaxed">{str}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Weaknesses Card (Red) */}
            <motion.div variants={itemVariants} className="glass-card p-5 rounded-2xl border-red-500/10 shadow-[0_0_20px_rgba(239,68,68,0.01)]">
              <h2 className="text-xs font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="text-red-400" size={16} /> Identified Weaknesses / Gaps
              </h2>
              <div className="space-y-2.5">
                {gaps.map((gap, idx) => (
                  <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-2.5 bg-red-950/20 border border-red-500/10 p-3.5 rounded-xl">
                    <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-mono font-bold mt-0.5 shrink-0">W{idx + 1}</span>
                    <p className="text-zinc-350 text-xs leading-relaxed">{gap}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Recommendations Section (Blue) */}
      <motion.div variants={itemVariants} className="glass-card p-6 rounded-3xl border-blue-500/10 shadow-[0_0_30px_rgba(59,130,246,0.02)] mb-8">
        <h2 className="text-sm font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
          <Sparkles className="text-blue-400" size={16} /> Actionable Focus Recommendations
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {recommendations.map((rec, idx) => (
            <motion.div key={idx} variants={badgeVariants} className="flex items-start gap-3 bg-blue-950/20 border border-blue-500/10 p-4 rounded-2xl">
              <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400 text-xs font-mono font-bold shrink-0 mt-0.5">{idx + 1}</div>
              <p className="text-zinc-355 text-xs leading-relaxed">{rec}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Suggested next topics to master */}
      <motion.div variants={itemVariants} className="glass-card p-6 rounded-3xl border-purple-500/10 shadow-[0_0_30px_rgba(168,85,247,0.02)] mb-10">
        <h2 className="text-sm font-bold text-zinc-300 font-display mb-4 uppercase tracking-wider flex items-center gap-2">
          <Compass className="text-purple-400" size={16} /> Recommended Next Topics to Master
        </h2>
        <div className="flex flex-wrap gap-2.5">
          {next.map((step, idx) => (
            <motion.span 
              key={idx} 
              variants={badgeVariants}
              className="text-xs font-semibold bg-purple-950/30 border border-purple-500/20 text-purple-300 px-3.5 py-2 rounded-xl flex items-center gap-2"
            >
              <Star size={11} className="fill-purple-300" />
              {step}
            </motion.span>
          ))}
        </div>
      </motion.div>

      {/* Action CTA triggers */}
      <motion.div variants={itemVariants} className="flex justify-center gap-4 pt-4">
        {/* CTA 1: Retake Interview */}
        <motion.button 
          onClick={onReset} 
          whileHover={{ scale: 1.05 }} 
          whileTap={{ scale: 0.95 }} 
          className="flex items-center gap-2 px-6 py-3.5 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-white font-semibold rounded-xl cursor-pointer transition-all duration-300"
        >
          <RefreshCw size={18} />
          Retake Interview
        </motion.button>

        {/* CTA 2: Try Harder Mode */}
        <motion.button 
          onClick={onReset} 
          whileHover={{ scale: 1.05 }} 
          whileTap={{ scale: 0.95 }} 
          className="flex items-center gap-2 px-6 py-3.5 bg-gradient-to-r from-purple-650 to-pink-650 text-white font-semibold rounded-xl cursor-pointer glow-btn-purple transition-all duration-300"
        >
          <Zap size={18} className="fill-white" />
          Try Harder Mode
        </motion.button>
      </motion.div>
    </motion.div>
  );
}
