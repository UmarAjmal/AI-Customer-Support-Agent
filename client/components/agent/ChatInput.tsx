"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { useAgent } from "../../hooks/useAgent";

export const ChatInput: React.FC = () => {
  const [text, setText] = useState("");
  const { sendMessage, isTyping } = useAgent();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize input height based on contents
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [text]);

  const handleSend = async () => {
    if (!text.trim() || isTyping) return;
    const msg = text.trim();
    setText("");
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    await sendMessage(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-3 bg-white border-t border-zinc-100/80 sticky bottom-0 z-10">
      <div className="flex items-end space-x-2 bg-zinc-50 border border-zinc-200 hover:border-zinc-300 rounded-[12px] px-3.5 py-2.5 transition-all duration-200 focus-within:ring-2 focus-within:ring-[#6C63FF]/20 focus-within:border-[#6C63FF]">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isTyping ? "AI is replying..." : "Ask me anything..."}
          disabled={isTyping}
          rows={1}
          className="flex-1 max-h-30 resize-none bg-transparent outline-none border-none font-sans text-sm text-zinc-800 placeholder-zinc-400 select-text disabled:opacity-50"
          style={{ height: "auto" }}
          aria-label="Type your message"
        />
        
        <button
          onClick={handleSend}
          disabled={!text.trim() || isTyping}
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] text-white hover:opacity-90 shadow-[0_4px_12px_rgba(108,99,255,0.25)] active:scale-95 transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none disabled:shadow-none cursor-pointer"
          aria-label="Send message"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
