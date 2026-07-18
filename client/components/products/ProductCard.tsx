"use client";

import React, { useState } from "react";
import { Product } from "../../types/chat";
import { Star, ShoppingCart, Check, Bot } from "lucide-react";
import { useCart } from "../../hooks/useCart";
import { useAgent } from "../../hooks/useAgent";

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const { addItem } = useCart();
  const { sendMessage, toggleWidget, isOpen } = useAgent();
  const [added, setAdded] = useState(false);

  const handleAddToCart = () => {
    addItem(product);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleAskAI = async () => {
    if (!isOpen) {
      toggleWidget();
    }
    // Small delay to let the widget mount and open
    setTimeout(async () => {
      await sendMessage(`Tell me more about the ${product.name}`);
    }, 400);
  };

  return (
    <div className="flex flex-col bg-white border border-zinc-200/80 rounded-[16px] overflow-hidden hover:shadow-lg transition-all duration-300 group">
      {/* Product Image */}
      <div className="relative w-full h-56 bg-zinc-50 border-b border-zinc-100 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <span className="absolute top-3.5 left-3.5 px-2.5 py-1 rounded-full bg-[#1A1A2E] text-[9px] font-bold text-white uppercase tracking-wider">
          {product.category}
        </span>
      </div>

      {/* Product Information */}
      <div className="p-4.5 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-center space-x-1 mb-2">
            <div className="flex text-amber-400">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`w-3.5 h-3.5 ${
                    i < Math.floor(product.rating)
                      ? "fill-current"
                      : "text-zinc-200"
                  }`}
                />
              ))}
            </div>
            <span className="text-[10px] text-zinc-500 font-bold font-sans">
              {product.rating} ({product.reviewsCount} reviews)
            </span>
          </div>

          <h3 className="font-sans font-bold text-base text-zinc-950 leading-snug group-hover:text-[#6C63FF] transition-colors">
            {product.name}
          </h3>
          
          <p className="text-xs text-zinc-500 font-medium font-sans mt-1.5 line-clamp-2 leading-relaxed">
            {product.description}
          </p>
        </div>

        {/* Pricing and Actions */}
        <div className="mt-5">
          <div className="flex justify-between items-center mb-4 pt-3 border-t border-zinc-100">
            <span className="font-sans font-black text-lg text-zinc-950">
              Rs. {product.price.toLocaleString("en-PK")}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {/* Add to Cart button */}
            <button
              onClick={handleAddToCart}
              className={`flex items-center justify-center space-x-1.5 px-3 py-2.5 rounded-xl text-xs font-bold font-sans transition-all duration-200 cursor-pointer ${
                added
                  ? "bg-emerald-500 text-white"
                  : "bg-[#1A1A2E] text-white hover:opacity-95 active:scale-95 shadow-sm"
              }`}
            >
              {added ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Added</span>
                </>
              ) : (
                <>
                  <ShoppingCart className="w-4 h-4" />
                  <span>Add to Cart</span>
                </>
              )}
            </button>

            {/* Ask AI button */}
            <button
              onClick={handleAskAI}
              className="flex items-center justify-center space-x-1.5 px-3 py-2.5 bg-zinc-50 hover:bg-zinc-100 text-zinc-700 hover:text-zinc-900 border border-zinc-200 rounded-xl text-xs font-bold font-sans transition-all duration-200 active:scale-95 cursor-pointer"
            >
              <Bot className="w-4 h-4 text-[#6C63FF]" />
              <span>Ask AI</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
