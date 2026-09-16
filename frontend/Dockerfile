# ============================================================
# Frontend Dockerfile — Node 20 + Vite
# ============================================================

FROM node:20-slim

WORKDIR /app

# Copy dependency definitions
COPY package*.json ./

# Clean install dependencies
RUN npm ci

# Copy source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Vite runs on host 0.0.0.0 for container networking
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
