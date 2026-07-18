"use client";

import { useEffect } from "react";
import { fetchCatalog, fetchCategories } from "../lib/api";

/** Warm catalog + categories cache as soon as the app loads */
export default function CatalogPrefetch() {
  useEffect(() => {
    void Promise.all([fetchCatalog(), fetchCategories()]).catch(() => {
      /* ignore — pages will retry */
    });
  }, []);
  return null;
}
