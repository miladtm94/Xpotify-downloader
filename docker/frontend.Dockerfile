FROM node:22-bookworm-slim

WORKDIR /app/app/frontend

COPY app/frontend/package*.json ./

RUN npm install

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
