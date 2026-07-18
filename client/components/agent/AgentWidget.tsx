"use client";

import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAgent } from "../../hooks/useAgent";
import ChatHeader from "./ChatHeader";
import ChatHistory from "./ChatHistory";
import QuickReplies from "./QuickReplies";
import ChatInput from "./ChatInput";

export const AgentWidget: React.FC = () => {
  const { isOpen } = useAgent();

  // Prevent background scrolling when chat is full screen on mobile
  useEffect(() => {
    if (isOpen) {
      const isMobile = window.innerWidth < 640;
      if (isMobile) {
        document.body.style.overflow = "hidden";
      }
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 40, scale: 0.95 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="fixed inset-0 sm:inset-auto sm:bottom-[96px] sm:right-6 z-50 w-full h-full sm:w-[380px] sm:h-[600px] flex flex-col bg-white sm:rounded-[20px] sm:border sm:border-zinc-200/80 shadow-[0_12px_40px_rgba(0,0,0,0.12)] sm:shadow-[0_20px_50px_rgba(26,26,46,0.15)] overflow-hidden"
          role="dialog"
          aria-label="ShopEase AI support chat widget"
        >
          {/* Header section */}
          <ChatHeader />

          {/* Messages Feed area */}
          <ChatHistory />

          {/* Quick Actions Chips */}
          <QuickReplies />

          {/* Text Area & Submit Bar */}
          <ChatInput />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AgentWidget;
