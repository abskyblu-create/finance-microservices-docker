FROM node:20-alpine

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY package*.json ./
RUN npm install

COPY . .

RUN mkdir -p /app/node_modules /app/.vite && chown -R app:app /app

USER app

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD wget -qO- http://localhost:5173 > /dev/null || exit 1

CMD ["npm", "run", "dev"]
