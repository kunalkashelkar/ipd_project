# ============================================================
# Frontend Dockerfile — Node + Vite
# ============================================================

FROM node:20-slim

WORKDIR /app

# The node modules could be cached in a real environment, but we'll run dev for Phase 1.
COPY frontend/package.json ./

# Because we are running dev, we just expose the vite port
EXPOSE 5173

# Vite runs on host 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host"]
