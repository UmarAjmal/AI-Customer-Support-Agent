"use client";

import React from "react";
import { Minus, X, Trash2 } from "lucide-react";
import { useAgent } from "../../hooks/useAgent";

export const ChatHeader: React.FC = () => {
  const { minimizeWidget, closeWidget, clearChat, humanHandoff } = useAgent();

  return (
    <div className="relative flex items-center justify-between px-5 py-4 bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] text-white rounded-t-[20px] shadow-md select-none">
      <div className="flex items-center space-x-3">
        {/* Robot Avatar */}
        <div className="relative w-10 h-10 rounded-full bg-white/20 flex items-center justify-center border border-white/25 backdrop-blur-sm shadow-inner">
          <svg
            className="w-6 h-6 text-white"
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
          {/* Glowing Status Dot */}
          <span className={`absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full border-2 border-white ${
            humanHandoff ? "bg-amber-400" : "bg-emerald-400"
          }`}>
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${
              humanHandoff ? "bg-amber-400" : "bg-emerald-400"
            }`} />
          </span>
        </div>

        {/* Title / Status */}
        <div>
          <h2 className="font-sans font-bold text-sm tracking-tight text-white flex items-center gap-1">
            ShopEase AI
          </h2>
          <p className="font-sans text-[11px] text-white/90 font-medium">
            {humanHandoff ? "Connecting to Live Agent..." : "Typically replies instantly"}
          </p>
        </div>
      </div>

      {/* Control Buttons */}
      <div className="flex items-center space-x-1.5">
        {/* Reset Chat */}
        <button
          onClick={clearChat}
          className="w-8 h-8 rounded-full flex items-center justify-center bg-white/10 hover:bg-white/20 transition-all text-white border border-white/10 duration-200"
          title="Reset Chat"
          aria-label="Reset Chat"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>

        {/* Minimize */}
        <button
          onClick={minimizeWidget}
          className="w-8 h-8 rounded-full flex items-center justify-center bg-white/10 hover:bg-white/20 transition-all text-white border border-white/10 duration-200"
          title="Minimize Chat"
          aria-label="Minimize Chat"
        >
          <Minus className="w-4 h-4" />
        </button>

        {/* Close */}
        <button
          onClick={closeWidget}
          className="w-8 h-8 rounded-full flex items-center justify-center bg-white/10 hover:bg-white/20 transition-all text-white border border-white/10 duration-200"
          title="Close Widget"
          aria-label="Close Widget"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;
