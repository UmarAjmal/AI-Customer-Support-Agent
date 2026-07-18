"use client";

import React, { useState } from "react";
import { Message, Product, Order } from "../../types/chat";
import { Star, ShoppingCart, Check, Truck, Box, MapPin, Calendar, ExternalLink } from "lucide-react";
import { useCartStore } from "../../store/cartStore";
import { motion } from "framer-motion";

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const { role, content, products, order, timestamp, handoff } = message;
  const isBot = role === "assistant";
  const addItem = useCartStore((state) => state.addItem);
  const [addedProductIds, setAddedProductIds] = useState<Record<string, boolean>>({});

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const handleAddToCart = (product: Product) => {
    addItem(product);
    setAddedProductIds((prev) => ({ ...prev, [product.id]: true }));
    setTimeout(() => {
      setAddedProductIds((prev) => ({ ...prev, [product.id]: false }));
    }, 2000);
  };

  // Simple and safe custom markdown parser
  const renderMarkdown = (text: string) => {
    if (!text) return null;

    // Split text by code blocks first
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      // Monospace Code Block
      if (part.startsWith("```") && part.endsWith("```")) {
        const lines = part.slice(3, -3).trim().split("\n");
        // Separate language label if present
        let language = "code";
        let codeLines = lines;
        if (lines[0] && !lines[0].includes(" ") && lines[0].length < 15) {
          language = lines[0];
          codeLines = lines.slice(1);
        }
        const codeText = codeLines.join("\n");

        return (
          <div key={index} className="my-3 border border-zinc-200 rounded-lg overflow-hidden font-mono text-[12px] bg-zinc-900 text-zinc-100 select-text">
            <div className="flex justify-between items-center px-3 py-1.5 bg-zinc-800 border-b border-zinc-700/60 text-zinc-400 text-[10px] uppercase tracking-wider font-sans font-bold">
              <span>{language}</span>
              <button
                onClick={() => navigator.clipboard.writeText(codeText)}
                className="hover:text-white transition-colors cursor-pointer"
              >
                Copy
              </button>
            </div>
            <pre className="p-3.5 overflow-x-auto whitespace-pre leading-relaxed">
              <code>{codeText}</code>
            </pre>
          </div>
        );
      }

      // Plain text with inline formatting
      const lines = part.split("\n");
      return (
        <div key={index} className="space-y-1.5">
          {lines.map((line, lineIdx) => {
            // Unordered Lists
            if (line.trim().startsWith("* ") || line.trim().startsWith("- ")) {
              const content = line.trim().substring(2);
              return (
                <ul key={lineIdx} className="list-disc pl-5 my-1 text-inherit">
                  <li>{parseInlineMarkdown(content)}</li>
                </ul>
              );
            }

            // Ordered Lists
            const olMatch = line.trim().match(/^(\d+)\.\s(.*)/);
            if (olMatch) {
              const num = olMatch[1];
              const content = olMatch[2];
              return (
                <ol key={lineIdx} className="list-decimal pl-5 my-1 text-inherit">
                  <li value={parseInt(num)}>{parseInlineMarkdown(content)}</li>
                </ol>
              );
            }

            // Headers (e.g. ### Header)
            if (line.trim().startsWith("### ")) {
              return (
                <h4 key={lineIdx} className="text-sm font-bold mt-2.5 mb-1.5 text-zinc-900 font-sans">
                  {parseInlineMarkdown(line.trim().substring(4))}
                </h4>
              );
            }
            if (line.trim().startsWith("## ")) {
              return (
                <h3 key={lineIdx} className="text-base font-bold mt-3 mb-2 text-zinc-900 font-sans">
                  {parseInlineMarkdown(line.trim().substring(3))}
                </h3>
              );
            }

            // Standard line
            return (
              <p key={lineIdx} className="leading-relaxed whitespace-pre-wrap">
                {parseInlineMarkdown(line)}
              </p>
            );
          })}
        </div>
      );
    });
  };

  // Parses bold, italics, links inline
  const parseInlineMarkdown = (text: string) => {
    // Matches: [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    // Matches: **text**
    const boldRegex = /\*\*([^*]+)\*\*/g;
    // Matches: *text*
    const italicRegex = /\*([^*]+)\*/g;

    let elements: React.ReactNode[] = [text];

    // Replace Bold
    elements = elements.flatMap((el) => {
      if (typeof el !== "string") return el;
      const parts = el.split(/\*\*([^*]+)\*\*/g);
      return parts.map((part, i) => (i % 2 === 1 ? <strong key={i} className="font-bold font-sans text-zinc-900">{part}</strong> : part));
    });

    // Replace Italics
    elements = elements.flatMap((el) => {
      if (typeof el !== "string") return el;
      const parts = el.split(/\*([^*]+)\*/g);
      return parts.map((part, i) => (i % 2 === 1 ? <em key={i} className="italic text-zinc-700">{part}</em> : part));
    });

    // Replace Links
    elements = elements.flatMap((el) => {
      if (typeof el !== "string") return el;
      
      const result: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      
      linkRegex.lastIndex = 0; // reset regex index
      while ((match = linkRegex.exec(el)) !== null) {
        const matchIndex = match.index;
        const [full, linkText, linkUrl] = match;
        
        if (matchIndex > lastIndex) {
          result.push(el.substring(lastIndex, matchIndex));
        }
        
        result.push(
          <a
            key={matchIndex}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-[#6C63FF] hover:underline font-semibold gap-0.5"
          >
            {linkText}
            <ExternalLink className="w-2.5 h-2.5" />
          </a>
        );
        lastIndex = linkRegex.lastIndex;
      }
      
      if (lastIndex < el.length) {
        result.push(el.substring(lastIndex));
      }
      
      return result.length > 0 ? result : el;
    });

    return <>{elements}</>;
  };

  // Helper to render shipping tracker progress
  const renderShippingProgress = (status: Order["status"]) => {
    const steps: { label: string; icon: React.ReactNode; matched: boolean }[] = [
      { label: "Processing", icon: <Box className="w-4 h-4" />, matched: true },
      { label: "Shipped", icon: <Truck className="w-4 h-4" />, matched: status === "in_transit" || status === "delivered" },
      { label: "Out for Delivery", icon: <MapPin className="w-4 h-4" />, matched: status === "delivered" },
      { label: "Delivered", icon: <Calendar className="w-4 h-4" />, matched: status === "delivered" },
    ];

    let activeStepIdx = 0;
    if (status === "in_transit") activeStepIdx = 1;
    if (status === "delivered") activeStepIdx = 3;

    return (
      <div className="mt-4 p-3 bg-zinc-50 border border-zinc-150 rounded-xl">
        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-bold uppercase tracking-wider mb-3">
          <span>Shipment Status</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-sans border ${
            status === "delivered"
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : status === "in_transit"
              ? "bg-blue-50 text-blue-700 border-blue-200"
              : "bg-amber-50 text-amber-700 border-amber-200"
          }`}>
            {status.replace("_", " ")}
          </span>
        </div>
        
        {/* Stepper Dots & Line */}
        <div className="relative flex justify-between items-center w-full px-2">
          {/* Progress Bar Background */}
          <div className="absolute top-[15px] left-8 right-8 h-1 bg-zinc-200 z-0" />
          {/* Progress Bar Active */}
          <div
            className="absolute top-[15px] left-8 h-1 bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] z-0 transition-all duration-500"
            style={{ width: `${(activeStepIdx / 3) * 80}%` }}
          />

          {steps.map((step, idx) => {
            const isCompleted = idx <= activeStepIdx;
            return (
              <div key={idx} className="relative z-10 flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all duration-300 shadow-sm ${
                    isCompleted
                      ? "bg-gradient-to-r from-[#6C63FF] to-[#4ECDC4] text-white border-transparent"
                      : "bg-white text-zinc-400 border-zinc-200"
                  }`}
                >
                  {step.icon}
                </div>
                <span className={`text-[10px] font-bold mt-1.5 text-center leading-tight max-w-[65px] ${
                  isCompleted ? "text-zinc-800 font-semibold" : "text-zinc-400"
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className={`flex w-full mb-4.5 group select-none ${isBot ? "justify-start" : "justify-end"}`}>
      <div className={`flex items-start max-w-[85%] sm:max-w-[80%] space-x-2.5 ${isBot ? "" : "flex-row-reverse space-x-reverse"}`}>
        
        {/* Avatar */}
        {isBot && (
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
        )}

        {/* Message Bubble Container */}
        <div className="flex flex-col space-y-1">
          {/* Bubble */}
          <div
            className={`px-4 py-3 rounded-[20px] text-sm select-text font-sans font-normal leading-relaxed shadow-sm transition-all duration-300 border ${
              isBot
                ? "bg-white text-zinc-800 border-zinc-200/60 rounded-tl-[4px] shadow-zinc-100/50"
                : "bg-gradient-to-br from-[#1A1A2E] to-[#2E2E4E] text-white border-transparent rounded-tr-[4px] shadow-[#1A1A2E]/10"
            }`}
          >
            {/* Message Body text */}
            <div className="text-zinc-800 font-sans leading-relaxed select-text">
              {isBot ? (
                <div className="text-inherit select-text prose prose-zinc max-w-none">
                  {renderMarkdown(content)}
                </div>
              ) : (
                <span className="text-white select-text font-medium whitespace-pre-wrap">{content}</span>
              )}
            </div>

            {/* Product Cards Grid */}
            {products && products.length > 0 && (
              <div className="mt-3.5 space-y-3">
                {products.map((prod) => (
                  <div
                    key={prod.id}
                    className="flex flex-col sm:flex-row items-stretch border border-zinc-150 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200"
                  >
                    {/* Product Image */}
                    <div className="relative w-full sm:w-24.5 h-28 sm:h-auto flex-shrink-0 bg-zinc-50 border-b sm:border-b-0 sm:border-r border-zinc-100">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={prod.image}
                        alt={prod.name}
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded-full bg-[#6C63FF] text-[8px] font-bold text-white uppercase tracking-wider">
                        {prod.category}
                      </span>
                    </div>

                    {/* Product Details */}
                    <div className="p-3.5 flex flex-col justify-between flex-1">
                      <div>
                        <h4 className="font-sans font-bold text-[13px] text-zinc-950 leading-tight">
                          {prod.name}
                        </h4>
                        <p className="text-[10px] text-zinc-400 mt-1 line-clamp-2">
                          {prod.description}
                        </p>
                        
                        {/* Rating */}
                        <div className="flex items-center space-x-1 mt-1.5">
                          <div className="flex text-amber-400">
                            {[...Array(5)].map((_, i) => (
                              <Star
                                key={i}
                                className={`w-3 h-3 ${
                                  i < Math.floor(prod.rating)
                                    ? "fill-current"
                                    : "text-zinc-200"
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-[10px] text-zinc-500 font-bold">
                            {prod.rating} ({prod.reviewsCount})
                          </span>
                        </div>
                      </div>

                      {/* Price & Add to Cart button */}
                      <div className="flex justify-between items-center mt-3 pt-2 border-t border-zinc-100">
                        <span className="font-sans font-extrabold text-[14px] text-zinc-950">
                          ${prod.price}
                        </span>

                        <button
                          onClick={() => handleAddToCart(prod)}
                          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-200 cursor-pointer ${
                            addedProductIds[prod.id]
                              ? "bg-emerald-500 text-white shadow-[0_4px_10px_rgba(16,185,129,0.2)]"
                              : "bg-[#1A1A2E] text-white hover:opacity-90 active:scale-95 shadow-sm"
                          }`}
                        >
                          {addedProductIds[prod.id] ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>Added</span>
                            </>
                          ) : (
                            <>
                              <ShoppingCart className="w-3.5 h-3.5" />
                              <span>Add to Cart</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Order Card */}
            {order && (
              <div className="mt-3.5 p-3.5 border border-zinc-150 rounded-xl bg-white text-zinc-800 shadow-sm">
                <div className="flex justify-between items-center border-b border-zinc-100 pb-2">
                  <div>
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">Order ID</span>
                    <span className="text-xs font-bold text-zinc-900 font-mono">{order.id}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">Est. Delivery</span>
                    <span className="text-xs font-bold text-zinc-900">{order.estimatedDelivery}</span>
                  </div>
                </div>

                {/* Items List */}
                <div className="py-2.5 border-b border-zinc-100 space-y-1.5">
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">Items</span>
                  {order.items.map((item, idx) => (
                    <div key={idx} className="flex justify-between text-xs text-zinc-700">
                      <span>
                        {item.name} <strong className="text-zinc-400">x{item.quantity}</strong>
                      </span>
                      <span className="font-semibold">${(item.price * item.quantity).toFixed(2)}</span>
                    </div>
                  ))}
                  <div className="flex justify-between text-xs pt-1.5 border-t border-zinc-50 font-bold text-zinc-950">
                    <span>Total</span>
                    <span>${order.total.toFixed(2)}</span>
                  </div>
                </div>

                {/* Carrier and Tracking Details */}
                <div className="pt-2 flex justify-between items-center text-xs">
                  <div>
                    <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">Carrier</span>
                    <span className="font-semibold text-zinc-700">{order.carrier}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">Tracking #</span>
                    <span className="font-semibold text-zinc-700 font-mono text-[11px]">{order.trackingNumber}</span>
                  </div>
                </div>

                {/* Stepper Status tracker */}
                {renderShippingProgress(order.status)}
              </div>
            )}
          </div>

          {/* Time stamp */}
          <span className={`text-[10px] text-zinc-400 font-semibold font-sans px-1.5 mt-0.5 ${
            isBot ? "text-left" : "text-right"
          }`}>
            {formatTime(timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
