"use client";

import React, { useEffect, useRef } from "react";
import { useAgent } from "../../hooks/useAgent";
import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";

export const ChatHistory: React.FC = () => {
  const { messages, isTyping } = useAgent();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom of the chat area whenever messages change or typing begins
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 bg-zinc-50/50 space-y-4 scrollbar-thin scrollbar-thumb-zinc-200"
      style={{ scrollBehavior: "smooth" }}
    >
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}

      {isTyping && (
        <div className="flex justify-start items-start space-x-2.5 mb-4.5 animate-pulse">
          <div className="flex-shrink-0 w-8.5 h-8.5 rounded-full bg-gradient-to-tr from-[#6C63FF] to-[#4ECDC4] flex items-center justify-center text-white border border-[#6C63FF]/15 shadow-sm">
            <svg
              className="w-5 h-5 text-white"
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
          </div>
          <TypingIndicator />
        </div>
      )}

      {/* Anchor for auto scroll */}
      <div ref={chatEndRef} />
    </div>
  );
};

export default ChatHistory;
