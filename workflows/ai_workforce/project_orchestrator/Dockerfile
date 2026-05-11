FROM node:24-alpine

WORKDIR /app/workflows/ai_workforce

COPY workflows/ai_workforce/package*.json ./
RUN npm ci --omit=dev

COPY workflows/ai_workforce ./

ENV PORT=3000
EXPOSE 3000

CMD ["node", "project_orchestrator/nexus_control_api.js"]
