"use client";

import React from "react";

export const Footer: React.FC = () => {
  return (
    <footer className="bg-zinc-900 border-t border-zinc-800 text-zinc-400 py-10 mt-auto select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs font-semibold tracking-wider font-sans">
        <p className="mb-2">© {new Date().getFullYear()} ShopEase. All rights reserved.</p>
        <p className="text-zinc-600">Styled with Tailwind CSS & Framer Motion. Enabled with ShopEase support AI.</p>
      </div>
    </footer>
  );
};

export default Footer;
