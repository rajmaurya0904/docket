---
title: Health check
description: A tiny endpoint written with an api block.
order: 2
---

# Health check

Endpoints can also be written as an `api` block, which is handy when a prose
page is more than you need.

```api
GET /health
summary: Returns `ok` while the service is up.
param verbose query boolean: Include dependency status
header Accept: application/json
response 200:
  { "status": "ok" }
response 503:
  { "status": "degraded", "failing": ["database"] }
```
