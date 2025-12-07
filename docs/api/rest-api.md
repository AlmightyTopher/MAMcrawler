# MAMcrawler REST API Reference

Complete technical reference for the MAMcrawler REST API, including all endpoints, authentication, and usage examples.

## Overview

The MAMcrawler API provides comprehensive REST endpoints for managing audiobook discovery, metadata, downloads, and system administration.

**Base URL:** `http://localhost:8000/api`  
**Version:** 1.0.0  
**Authentication:** API Key (routes), JWT (admin panel)

## Authentication

### API Key Authentication
```http
X-API-Key: your-secret-api-key
```

### JWT Authentication (Admin Panel)
```http
Authorization: Bearer <jwt-token>
```

## Response Format

All responses follow a consistent format:

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "error": null,
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

## Books API

### GET /books
Retrieve paginated list of books with filtering.

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `page_size` (integer): Items per page (default: 50, max: 100)
- `search` (string): Search in title, author, series
- `status` (string): Filter by status (active, duplicate, archived)
- `author` (string): Filter by author name
- `series` (string): Filter by series name
- `sort_by` (string): Sort field (title, author, created_at, updated_at)
- `sort_order` (string): Sort direction (asc, desc)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/books?page=1&page_size=20&search=wind&status=active" \
  -H "X-API-Key: your-api-key"
```

### POST /books
Create a new book.

**Request Body:**
```json
{
  "title": "The Name of the Wind",
  "author": "Patrick Rothfuss",
  "series": "The Kingkiller Chronicle",
  "series_number": "1",
  "isbn": "9780756404741",
  "import_source": "manual"
}
```

### GET /books/{book_id}
Get detailed book information.

### PUT /books/{book_id}
Update book information.

### GET /books/search
Search books by query string.

**Query Parameters:**
- `q` (string): Search query (required)
- `limit` (integer): Maximum results (default: 20, max: 100)
- `fields` (string): Fields to search (title, author, series, description)

## Downloads API

### GET /downloads
List downloads with filtering.

**Query Parameters:**
- `status` (string): Filter by status (queued, downloading, completed, failed, abandoned)
- `source` (string): Filter by source (MAM, GoogleBooks, Goodreads, Manual)
- `limit` (integer): Maximum results (default: 100)

### POST /downloads
Queue a new download.

**Request Body:**
```json
{
  "book_id": 123,
  "title": "The Name of the Wind",
  "author": "Patrick Rothfuss",
  "source": "MAM",
  "magnet_link": "magnet:?xt=urn:btih:abc123def456"
}
```

### PUT /downloads/{download_id}/status
Update download status.

## System API

### GET /system/health
Comprehensive health check (public endpoint).

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "components": {
      "database": {"status": "healthy"},
      "scheduler": {"status": "healthy"},
      "qbittorrent": {"status": "healthy"},
      "audiobookshelf": {"status": "healthy"}
    }
  }
}
```

### GET /system/stats
System-wide statistics including books, series, authors, and download metrics.

## Real-time Updates

### WebSocket Connection
Connect to real-time updates: `ws://localhost:8000/ws`

### Authentication
```javascript
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your-jwt-token'
}));
```

### Subscribe to Updates
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['downloads', 'books', 'system']
}));
```

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (validation error)
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Unprocessable Entity
- `429` - Too Many Requests
- `500` - Internal Server Error

### Error Response Format
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {"title": ["This field is required"]}
  }
}
```

## Rate Limiting

- **General API:** 1000 requests/hour
- **Search:** 100 requests/minute
- **Bulk Operations:** 50 requests/hour

## Code Examples

### Python Client
```python
import requests

class MAMcrawlerAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {'X-API-Key': api_key}

    def get_books(self, **filters):
        response = requests.get(f"{self.base_url}/books", headers=self.headers, params=filters)
        return response.json()['data']

# Usage
api = MAMcrawlerAPI('http://localhost:8000/api', 'your-api-key')
books = api.get_books(page=1, page_size=20, status='active')
```

### JavaScript Client
```javascript
class MAMcrawlerAPI {
  constructor(baseURL, apiKey) {
    this.client = axios.create({
      baseURL,
      headers: { 'X-API-Key': apiKey }
    });
  }

  async getBooks(options = {}) {
    const response = await this.client.get('/books', { params: options });
    return response.data.data;
  }
}
```

## Security Considerations

- Store API keys securely (environment variables, key management systems)
- Use HTTPS in production
- Implement proper CORS policies
- Regular security audits and updates

## Additional Resources

- [WebSocket Events](websocket.md) - Real-time event handling
- [Authentication Guide](authentication.md) - Detailed auth setup
- [Rate Limiting](rate-limiting.md) - Usage limits and quotas
- [Error Codes](errors.md) - Complete error reference

---

*Last updated: November 30, 2025*