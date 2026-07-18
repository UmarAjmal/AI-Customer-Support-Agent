"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAgent } from "../../hooks/useAgent";

interface AgentButtonProps {
  /** When true, the button renders without fixed positioning so it can be
   *  embedded inside a parent container (e.g. the products page side nav). */
  embedded?: boolean;
}

export const AgentButton: React.FC<AgentButtonProps> = ({ embedded = false }) => {
  const { isOpen, toggleWidget, unreadCount } = useAgent();
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={`${embedded ? "relative" : "fixed bottom-6 right-6 z-50"} flex items-center select-none`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Tooltip */}
      <AnimatePresence>
        {showTooltip && !isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 15, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 15, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="hidden sm:block mr-3 px-3 py-2 bg-[#1A1A2E] text-white text-[12px] font-sans font-semibold rounded-lg shadow-lg border border-white/5 whitespace-nowrap pointer-events-none"
          >
            Need Help? Chat with ShopEase AI
            <div className="absolute right-[-4px] top-[14px] w-2 h-2 bg-[#1A1A2E] rotate-45 border-r border-t border-white/5" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Action Button */}
      <div className="relative">
        {/* Glowing Pulse Rings */}
        {!isOpen && (
          <>
            <motion.div
              animate={{
                scale: [1, 1.35, 1.6],
                opacity: [0.6, 0.25, 0],
              }}
              transition={{
                duration: 2.2,
                repeat: Infinity,
                ease: "easeOut",
              }}
              className="absolute inset-0 rounded-full bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] -z-10 blur-[1px]"
            />
            <motion.div
              animate={{
                scale: [1, 1.25, 1.45],
                opacity: [0.4, 0.15, 0],
              }}
              transition={{
                duration: 2.2,
                delay: 0.8,
                repeat: Infinity,
                ease: "easeOut",
              }}
              className="absolute inset-0 rounded-full bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] -z-10 blur-[1px]"
            />
          </>
        )}

        {/* Button body */}
        <motion.button
          onClick={toggleWidget}
          whileHover={{ scale: 1.08, rotate: 10 }}
          whileTap={{ scale: 0.94 }}
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="w-[60px] h-[60px] rounded-full flex items-center justify-center bg-gradient-to-br from-[#6C63FF] to-[#4ECDC4] text-white shadow-[0_10px_40px_rgba(108,99,255,0.38)] cursor-pointer outline-none border-none relative z-10"
          aria-label={isOpen ? "Close AI Support chat" : "Open AI Support chat"}
        >
          {isOpen ? (
            // Close SVG
            <svg
              className="w-7 h-7"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          ) : (
            // Robot Icon
            <svg
              className="w-7 h-7"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h.01M15 9h.01M8 13h8"
              />
            </svg>
          )}

          {/* Unread Message Badge */}
          <AnimatePresence>
            {unreadCount > 0 && !isOpen && (
              <motion.span
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="absolute -top-1 -right-1 min-w-[20px] h-[20px] px-1 bg-rose-500 rounded-full flex items-center justify-center text-[10px] font-sans font-bold text-white border-2 border-white shadow-md z-20"
              >
                {unreadCount}
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </div>
    </div>
  );
};

export default AgentButton;
