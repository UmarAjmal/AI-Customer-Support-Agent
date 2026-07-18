"use client";

import React from "react";
import Navbar from "../../components/layout/Navbar";
import Footer from "../../components/layout/Footer";
import AgentButton from "../../components/agent/AgentButton";
import AgentWidget from "../../components/agent/AgentWidget";
import { AgentProvider } from "../../components/agent/AgentProvider";
import { Package, Bot } from "lucide-react";
import { useAgent } from "../../hooks/useAgent";
import { useOrders } from "../../hooks/useOrders";
import { formatPrice } from "../../lib/api";

function OrdersContent() {
  const { sendMessage, toggleWidget, isOpen } = useAgent();
  const { orders, loading, error } = useOrders();

  const handleTrackInAI = async (orderId: string) => {
    if (!isOpen) toggleWidget();
    setTimeout(async () => {
      await sendMessage(`Track order ${orderId}`);
    }, 400);
  };

  const getStatusColor = (status: string) => {
    if (status === "delivered") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (status === "in_transit") return "bg-blue-50 text-blue-700 border-blue-200";
    if (status === "cancelled") return "bg-red-50 text-red-700 border-red-200";
    return "bg-amber-50 text-amber-700 border-amber-200";
  };

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 font-sans text-zinc-800">
      <Navbar />

      <main className="max-w-4xl mx-auto w-full px-4 py-12 flex-1">
        <h1 className="text-3xl font-black text-zinc-950 mb-8 font-sans flex items-center gap-2.5">
          <Package className="w-8 h-8 text-[#6C63FF]" />
          <span>My Orders</span>
        </h1>

        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 rounded-2xl bg-zinc-200 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-sm mb-6">
            Could not load orders: {error}. Is the API running?
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <p className="text-zinc-500 text-sm">No orders found in the database yet.</p>
        )}

        <div className="space-y-6">
          {orders.map((order) => (
            <div
              key={order.id}
              className="bg-white border border-zinc-200 rounded-2xl p-5 sm:p-6 shadow-sm"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 border-b border-zinc-100 gap-4">
                <div>
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                    Order Reference
                  </span>
                  <span className="text-sm font-bold text-zinc-950 font-mono">{order.id}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2.5 py-1 text-xs font-bold rounded-full border ${getStatusColor(order.status)}`}
                  >
                    {order.status.replace("_", " ")}
                  </span>
                  <button
                    onClick={() => handleTrackInAI(order.id)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#6C63FF]/10 text-[#6C63FF] hover:bg-[#6C63FF]/15 text-[11px] font-bold rounded-lg transition-colors cursor-pointer"
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>Track with AI</span>
                  </button>
                </div>
              </div>

              <div className="py-4 space-y-3">
                {order.items.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-zinc-800">
                      {item.name}{" "}
                      <span className="text-zinc-400 font-normal">x{item.quantity}</span>
                    </span>
                    <span className="font-bold text-zinc-950">
                      {formatPrice(item.price * item.quantity)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-zinc-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">
                    Est. Delivery
                  </span>
                  <span className="font-semibold text-zinc-800">{order.estimatedDelivery}</span>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">
                    Courier
                  </span>
                  <span className="font-semibold text-zinc-800">{order.carrier}</span>
                </div>
                <div>
                  <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider block">
                    Tracking #
                  </span>
                  <span className="font-semibold text-zinc-800 font-mono">
                    {order.trackingNumber}
                  </span>
                </div>
              </div>

              <div className="pt-3 text-right text-sm font-bold text-zinc-950">
                Total: {formatPrice(order.total)}
              </div>
            </div>
          ))}
        </div>
      </main>

      <Footer />
      <AgentButton />
      <AgentWidget />
    </div>
  );
}

export default function OrdersPage() {
  return (
    <AgentProvider>
      <OrdersContent />
    </AgentProvider>
  );
}
