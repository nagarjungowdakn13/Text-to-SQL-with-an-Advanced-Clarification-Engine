FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
# Clean install of npm packages
RUN npm ci

COPY . .
# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
