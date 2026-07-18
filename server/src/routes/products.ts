import { Router, Request, Response } from "express";
import { MOCK_PRODUCTS } from "../lib/mockData";

const router = Router();

// GET /api/products — get all products (with optional category filter & search)
router.get("/", (req: Request, res: Response) => {
  const { category, search, limit } = req.query;

  let products = [...MOCK_PRODUCTS];

  if (typeof category === "string") {
    products = products.filter(
      (p) => p.category.toLowerCase() === category.toLowerCase()
    );
  }

  if (typeof search === "string" && search.trim()) {
    const q = search.toLowerCase();
    products = products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q)
    );
  }

  if (typeof limit === "string" && !isNaN(Number(limit))) {
    products = products.slice(0, Number(limit));
  }

  res.json({ data: products, count: products.length });
});

// GET /api/products/categories — list distinct categories
router.get("/categories", (_req: Request, res: Response) => {
  const categories = Array.from(new Set(MOCK_PRODUCTS.map((p) => p.category)));
  res.json({ data: categories });
});

// GET /api/products/:id — get single product by id
router.get("/:id", (req: Request, res: Response) => {
  const product = MOCK_PRODUCTS.find((p) => p.id === req.params.id);
  if (!product) {
    res.status(404).json({ error: `Product '${req.params.id}' not found` });
    return;
  }
  res.json({ data: product });
});

export default router;
