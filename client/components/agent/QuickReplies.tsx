"use client";

import React from "react";
import { useAgent } from "../../hooks/useAgent";
import { Search, Package, RefreshCcw, User, CreditCard, DollarSign } from "lucide-react";

interface QuickAction {
  label: string;
  icon: React.ReactNode;
}

export const QuickReplies: React.FC = () => {
  const { sendQuickReply, isTyping } = useAgent();

  const actions: QuickAction[] = [
    { label: "Find Product", icon: <Search className="w-3 h-3" /> },
    { label: "Track Order", icon: <Package className="w-3 h-3" /> },
    { label: "Return Item", icon: <RefreshCcw className="w-3 h-3" /> },
    { label: "Talk to Human", icon: <User className="w-3 h-3" /> },
    { label: "Payment Help", icon: <CreditCard className="w-3 h-3" /> },
    { label: "Refund Status", icon: <DollarSign className="w-3 h-3" /> },
  ];

  return (
    <div className="w-full bg-white border-t border-zinc-100/80 py-2.5">
      <div className="flex overflow-x-auto gap-2 px-4 scrollbar-none snap-x snap-mandatory touch-pan-x select-none">
        {actions.map((action, idx) => (
          <button
            key={idx}
            onClick={() => sendQuickReply(action.label)}
            disabled={isTyping}
            className="flex items-center space-x-1.5 flex-shrink-0 px-3 py-1.5 bg-zinc-50 border border-zinc-200/80 text-zinc-700 hover:bg-zinc-100 hover:border-zinc-300 text-[12px] font-sans font-semibold rounded-full cursor-pointer transition-all duration-200 shadow-sm active:scale-95 disabled:opacity-50 disabled:pointer-events-none snap-start"
          >
            {action.icon}
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickReplies;
