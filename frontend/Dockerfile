FROM node:20-slim

WORKDIR /app

# Instala dependencias primero (caché de capas)
COPY package.json ./
RUN npm install

# Código de la aplicación
COPY . .

EXPOSE 5173

# Desarrollo: servidor de Vite con hot-reload
CMD ["npm", "run", "dev"]
