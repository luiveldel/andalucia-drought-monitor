FROM node:22-bookworm-slim

WORKDIR /app

# Available at runtime (compose env_file / -e) and optionally at build time.
ARG VITE_CARTO_API_KEY=
ENV VITE_CARTO_API_KEY=${VITE_CARTO_API_KEY}

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
