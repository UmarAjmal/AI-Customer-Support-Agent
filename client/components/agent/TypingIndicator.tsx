"use client";

import React from "react";
import { motion } from "framer-motion";

export const TypingIndicator: React.FC = () => {
  const dotVariants = {
    initial: {
      y: 0,
      opacity: 0.4,
    },
    animate: {
      y: [0, -6, 0],
      opacity: [0.4, 1, 0.4],
    },
  };

  return (
    <div className="flex items-center space-x-1 px-4 py-3 bg-zinc-50 border border-zinc-100 rounded-2xl w-fit" aria-label="AI is typing">
      <div className="flex space-x-1 items-center h-3">
        {[0, 1, 2].map((index) => (
          <motion.span
            key={index}
            className="w-2 h-2 bg-zinc-400 rounded-full"
            variants={dotVariants}
            initial="initial"
            animate="animate"
            transition={{
              duration: 0.8,
              repeat: Infinity,
              repeatType: "loop",
              ease: "easeInOut",
              delay: index * 0.15,
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default TypingIndicator;
