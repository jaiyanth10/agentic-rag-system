# API Documentation - User Service

## Overview
The User Service handles authentication, user profiles, and session management.

## Base URL
```
Production: https://api.company.com/v1/users
Staging: https://staging-api.company.com/v1/users
Development: http://localhost:8000/v1/users
```

## Authentication

All endpoints require an API key in the header:
```
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key
1. Log into dashboard.company.com
2. Navigate to Settings → API Keys
3. Click "Generate New Key"
4. Store securely (we don't show it again!)

## Endpoints

### GET /users/{user_id}
Get user profile by ID.

**Parameters:**
- `user_id` (path, required): User's unique identifier

**Response:**
```json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "active",
  "roles": ["user", "beta_tester"]
}
```

**Status Codes:**
- 200: Success
- 404: User not found
- 401: Invalid API key
- 429: Rate limit exceeded (max 100 req/min)

### POST /users
Create a new user.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "password": "secure_password_123"
}
```

**Validation Rules:**
- Email must be unique
- Password: min 8 characters, must include numbers
- Name: 2-100 characters

**Response:**
```json
{
  "id": "usr_xyz789",
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "created_at": "2024-09-20T14:22:00Z",
  "status": "active"
}
```

### PUT /users/{user_id}
Update user profile.

**Request Body:**
```json
{
  "name": "Jane Doe",
  "notification_preferences": {
    "email": true,
    "sms": false
  }
}
```

**Note:** Email cannot be changed via this endpoint for security reasons.

### DELETE /users/{user_id}
Soft delete a user (marks as inactive).

**Response:**
```json
{
  "success": true,
  "message": "User deactivated successfully"
}
```

**Important:** Data is retained for 90 days for compliance. Use `/users/{user_id}/permanently-delete` for GDPR requests.

## Rate Limiting

- **Default**: 100 requests/minute per API key
- **Burst**: Up to 150 requests in 30 seconds
- **Headers**:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 85
  X-RateLimit-Reset: 1695234567
  ```

## Error Handling

All errors follow this format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is already registered",
    "field": "email",
    "docs": "https://docs.company.com/errors/validation"
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR`: Invalid input
- `NOT_FOUND`: Resource doesn't exist
- `UNAUTHORIZED`: Missing/invalid API key
- `RATE_LIMIT`: Too many requests
- `SERVER_ERROR`: Internal error (we're alerted automatically)

## Code Examples

### Python
```python
import requests

headers = {"Authorization": "Bearer YOUR_API_KEY"}
response = requests.get(
    "https://api.company.com/v1/users/usr_abc123",
    headers=headers
)
user = response.json()
```

### JavaScript
```javascript
const response = await fetch('https://api.company.com/v1/users/usr_abc123', {
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
});
const user = await response.json();
```

### cURL
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.company.com/v1/users/usr_abc123
```

## Webhooks

Subscribe to user events:
- `user.created`
- `user.updated`
- `user.deleted`

Configure at: dashboard.company.com/webhooks

## Testing

Use our test API keys (start with `test_`):
```
Test Key: test_sk_abc123xyz
```

Test mode:
- No real users created
- Rate limits relaxed (1000/min)
- Test credit card: 4242 4242 4242 4242

## Support

- **Docs**: docs.company.com/api
- **Status**: status.company.com
- **Support**: api-support@company.com
- **Slack**: #api-help (internal)

## Changelog

### v1.2.0 (2024-09-01)
- Added notification preferences
- Improved error messages
- New webhook: `user.updated`

### v1.1.0 (2024-06-15)
- Added rate limiting
- New endpoint: `PATCH /users/{id}/password`

### v1.0.0 (2024-01-01)
- Initial release
