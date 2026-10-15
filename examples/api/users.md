---
title: Users API
description: Endpoints for managing users.
---

# Users API

## GET /users

Retrieve a list of users.

### Response

```json
[
  { "id": 1, "name": "Alice" },
  { "id": 2, "name": "Bob" }
]
```

## POST /users

Create a new user.

### Request Body

```json
{ "name": "string" }
```

### Response

```json
{ "id": 3, "name": "Charlie" }
```