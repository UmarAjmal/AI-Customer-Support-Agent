"use client";

import React from "react";
import { useProducts } from "../../hooks/useProducts";
import ProductCard from "./ProductCard";

export const ProductGrid: React.FC = () => {
  const { products } = useProducts();

  return (
    <div className="w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
};

export default ProductGrid;
