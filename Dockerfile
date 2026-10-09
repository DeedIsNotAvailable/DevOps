# syntax=docker/dockerfile:1
FROM node:22-bookworm AS dependencies
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM node:22-bookworm AS browser
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY --from=dependencies /app/package*.json ./
COPY --from=dependencies /app/node_modules ./node_modules
RUN npx playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && chmod -R a+rX /ms-playwright

FROM browser AS production
ENV NODE_ENV=production
COPY --chown=node:node src/ ./src/
RUN mkdir -p /app/out && chown node:node /app/out
USER node
CMD ["node", "src/index.mjs"]
