"use client";

import React from "react";
import { ShoppingCart, Bot, Sparkles } from "lucide-react";
import { useCart } from "../../hooks/useCart";
import { useAgent } from "../../hooks/useAgent";
import Link from "next/link";

export const Navbar: React.FC = () => {
  const { totalItems } = useCart();
  const { toggleWidget, isOpen } = useAgent();

  return (
    <nav className="sticky top-0 z-40 w-full bg-white/80 border-b border-zinc-150 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo Section */}
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#6C63FF] to-[#4ECDC4] flex items-center justify-center text-white shadow-md">
              <span className="font-sans font-extrabold text-[18px]">S</span>
            </div>
            <Link href="/" className="font-sans font-black text-lg tracking-tight text-zinc-900 hover:opacity-90">
              Shop<span className="text-[#6C63FF]">Ease</span>
            </Link>
          </div>

          {/* Nav Links */}
          <div className="hidden md:flex space-x-8 text-sm font-semibold text-zinc-600 font-sans">
            <Link href="/" className="text-[#6C63FF] hover:text-[#6C63FF]">Home</Link>
            <Link href="/" className="hover:text-[#6C63FF] transition-colors">Shop</Link>
            <Link href="/" className="hover:text-[#6C63FF] transition-colors">Categories</Link>
            <Link href="/" className="hover:text-[#6C63FF] transition-colors">Deals</Link>
          </div>

          {/* Action Area */}
          <div className="flex items-center space-x-4">
            {/* Ask AI Navbar trigger */}
            <button
              onClick={toggleWidget}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-full text-xs font-bold font-sans cursor-pointer transition-all duration-200 border ${
                isOpen
                  ? "bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] text-white border-transparent shadow-[0_4px_12px_rgba(108,99,255,0.25)]"
                  : "bg-[#1A1A2E]/5 hover:bg-[#1A1A2E]/10 text-zinc-800 border-zinc-200"
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Ask AI</span>
              <Sparkles className="w-2.5 h-2.5" />
            </button>

            {/* Shopping Cart Indicator */}
            <div className="relative p-2 rounded-full bg-zinc-50 border border-zinc-200/80 hover:bg-zinc-100 transition-colors shadow-sm cursor-pointer group">
              <ShoppingCart className="w-4.5 h-4.5 text-zinc-800" />
              {totalItems > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4.5 min-w-[18px] px-1 items-center justify-center rounded-full bg-[#1A1A2E] text-[9px] font-sans font-bold text-white border border-white animate-bounce">
                  {totalItems}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
