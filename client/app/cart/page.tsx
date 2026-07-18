"use client";

import React from "react";
import Navbar from "../../components/layout/Navbar";
import Footer from "../../components/layout/Footer";
import AgentButton from "../../components/agent/AgentButton";
import AgentWidget from "../../components/agent/AgentWidget";
import { AgentProvider } from "../../components/agent/AgentProvider";
import { useCart } from "../../hooks/useCart";
import { Plus, Minus, Trash2, ShoppingBag, ArrowLeft } from "lucide-react";
import Link from "next/link";

function CartContent() {
  const { items, updateQuantity, removeItem, totalPrice, totalItems } = useCart();

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 font-sans text-zinc-800">
      <Navbar />

      <main className="max-w-4xl mx-auto w-full px-4 py-12 flex-1">
        <h1 className="text-3xl font-black text-zinc-950 mb-8 font-sans flex items-center gap-2.5">
          <ShoppingBag className="w-8 h-8 text-[#6C63FF]" />
          <span>Shopping Cart</span>
        </h1>

        {items.length === 0 ? (
          <div className="bg-white border border-zinc-200 p-10 rounded-2xl text-center shadow-sm">
            <div className="w-16 h-16 bg-zinc-50 text-zinc-400 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-150">
              <ShoppingBag className="w-7 h-7" />
            </div>
            <h2 className="text-lg font-bold text-zinc-950 mb-1">Your cart is empty</h2>
            <p className="text-zinc-400 text-xs mb-6">Looks like you haven&apos;t added any items to your bag yet.</p>
            <Link
              href="/"
              className="inline-flex items-center space-x-2 px-5 py-2.5 bg-[#1A1A2E] text-white text-xs font-bold rounded-xl hover:opacity-90 active:scale-95 transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Shopping</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cart Items List */}
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm space-y-4">
                {items.map((item) => (
                  <div key={item.product.id} className="flex items-center gap-4 py-3 border-b border-zinc-100 last:border-0">
                    {/* Image */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={item.product.image} alt={item.product.name} className="w-20 h-20 object-cover rounded-xl border border-zinc-100 bg-zinc-50" />
                    
                    {/* Title & Price */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-sans font-bold text-sm text-zinc-950 truncate">{item.product.name}</h3>
                      <p className="text-xs text-zinc-400 font-bold mt-0.5">{item.product.category}</p>
                      <p className="text-sm font-black text-[#6C63FF] mt-2">
                        Rs. {item.product.price.toLocaleString("en-PK")}
                      </p>
                    </div>

                    {/* Controls */}
                    <div className="flex items-center gap-2">
                      <div className="flex items-center border border-zinc-200 bg-zinc-50 rounded-lg p-0.5">
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity - 1)}
                          className="p-1 hover:bg-zinc-200 rounded text-zinc-500 transition-colors cursor-pointer"
                        >
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <span className="px-2.5 text-xs font-bold text-zinc-800">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.product.id, item.quantity + 1)}
                          className="p-1 hover:bg-zinc-200 rounded text-zinc-500 transition-colors cursor-pointer"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <button
                        onClick={() => removeItem(item.product.id)}
                        className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                        title="Remove item"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Order Summary */}
            <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm h-fit">
              <h2 className="text-base font-bold text-zinc-950 mb-4 pb-2 border-b border-zinc-100">Summary</h2>
              <div className="space-y-3 text-sm text-zinc-600 mb-6">
                <div className="flex justify-between">
                  <span>Total Items</span>
                  <span className="font-semibold text-zinc-950">{totalItems}</span>
                </div>
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="font-semibold text-zinc-950">
                    Rs. {totalPrice.toLocaleString("en-PK")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Shipping</span>
                  <span className="text-emerald-600 font-bold">FREE</span>
                </div>
                <div className="flex justify-between pt-3 border-t border-zinc-100 font-bold text-zinc-950 text-base">
                  <span>Total</span>
                  <span>Rs. {totalPrice.toLocaleString("en-PK")}</span>
                </div>
              </div>

              <Link
                href="/checkout"
                className="w-full flex items-center justify-center space-x-2 py-3 bg-gradient-to-r from-[#6C63FF] to-[#4D41DF] text-white text-xs font-black rounded-xl hover:opacity-95 shadow-[0_4px_12px_rgba(108,99,255,0.2)] active:scale-[0.98] transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18, fontVariationSettings: "'FILL' 1" }}>lock_person</span>
                <span>Proceed to Secure Checkout</span>
              </Link>

              <div className="mt-4 text-center">
                <Link href="/" className="text-xs text-zinc-400 hover:text-[#6C63FF] transition-colors font-medium">
                  Continue Shopping
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>

      <Footer />
      <AgentButton />
      <AgentWidget />
    </div>
  );
}

export default function CartPage() {
  return (
    <AgentProvider>
      <CartContent />
    </AgentProvider>
  );
}
