# MAMcrawler API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Response Format](#response-format)
5. [Error Handling](#error-handling)
6. [Books API](#books-api)
7. [Downloads API](#downloads-api)
8. [System API](#system-api)
9. [Series API](#series-api)
10. [Authors API](#authors-api)
11. [Metadata API](#metadata-api)
12. [Scheduler API](#scheduler-api)
13. [Admin API](#admin-api)
14. [Real-time Updates](#real-time-updates)
15. [WebSocket Endpoints](#websocket-endpoints)
16. [Security Considerations](#security-considerations)
17. [Rate Limiting](#rate-limiting)
18. [Code Examples](#code-examples)

---

## Overview

The MAMcrawler API provides a comprehensive REST interface for managing audiobook discovery, metadata, downloads, and system administration. The API supports CRUD operations, advanced filtering, pagination, and real-time updates via WebSocket.

**Version:** 1.0.0  
**Framework:** FastAPI  
**Database:** PostgreSQL  
**Authentication:** API Key (routes), JWT (admin panel)  

---

## Authentication

### API Key Authentication
Most API endpoints require an API key passed via the `X-API-Key` header:

```http
X-API-Key: your-secret-api-key
```

### JWT Authentication (Admin Panel)
Admin endpoints use JWT tokens for session management:

```http
Authorization: Bearer <jwt-token>
```

### Public Endpoints
The following endpoints are publicly accessible:
- `GET /api/system/health`
- `GET /api/system/stats`
- `POST /api/admin/auth/login`

---

## Base URL

```
http://localhost:8000/api
```

**Note:** Change `localhost:8000` to your server address and port.

---

## Response Format

All API responses follow a standard format:

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

### Success Response
```json
{
  "success": true,
  "data": {
    "books": [
      {
        "id": 123,
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "series": "The Kingkiller Chronicle",
        "series_number": "1",
        "status": "active",
        "import_source": "mam_scraper",
        "created_at": "2025-11-18T14:25:52.863Z",
        "updated_at": "2025-11-18T14:25:52.863Z"
      }
    ],
    "page_info": {
      "page": 1,
      "page_size": 50,
      "total_pages": 5,
      "total_items": 250
    }
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "title": ["This field is required"]
    }
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

---

## Error Handling

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate resource)
- `422` - Unprocessable Entity (validation failed)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

### Error Codes
| Code | Description |
|------|-------------|
| `AUTHENTICATION_ERROR` | Invalid or missing API key |
| `VALIDATION_ERROR` | Request data validation failed |
| `NOT_FOUND` | Requested resource not found |
| `DUPLICATE_RESOURCE` | Resource already exists |
| `PERMISSION_DENIED` | Insufficient permissions |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |
| `DATABASE_ERROR` | Database operation failed |
| `EXTERNAL_SERVICE_ERROR` | External service (qBittorrent, Audiobookshelf) error |

---

## Books API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/books` | List books with filtering and pagination |
| `POST` | `/books` | Create new book |
| `GET` | `/books/{book_id}` | Get book details |
| `PUT` | `/books/{book_id}` | Update book |
| `DELETE` | `/books/{book_id}` | Delete book (soft delete) |
| `GET` | `/books/search` | Search books |
| `GET` | `/books/series/{series_name}` | Get books by series |
| `GET` | `/books/incomplete-metadata` | Get books with incomplete metadata |
| `GET` | `/books/{book_id}/metadata-history` | Get metadata correction history |
| `PUT` | `/books/{book_id}/metadata-source` | Update metadata source tracking |

### GET /books

**Description:** Retrieve paginated list of books with optional filtering

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 50, max: 100) |
| `search` | string | No | Search in title, author, series |
| `status` | string | No | Filter by status (active, duplicate, archived) |
| `author` | string | No | Filter by author name |
| `series` | string | No | Filter by series name |
| `sort_by` | string | No | Sort field (title, author, created_at, updated_at) |
| `sort_order` | string | No | Sort direction (asc, desc) |

**Request Example:**
```bash
curl -X GET "http://localhost:8000/api/books?page=1&page_size=20&search=wind&status=active&sort_by=title&sort_order=asc" \
  -H "X-API-Key: your-secret-api-key"
```

**Response Example:**
```json
{
  "success": true,
  "data": {
    "books": [
      {
        "id": 123,
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "series": "The Kingkiller Chronicle",
        "series_number": "1",
        "isbn": "9780756404741",
        "asin": "B007978NPG",
        "publisher": "DAW Books",
        "published_year": 2007,
        "duration_minutes": 1260,
        "description": "Told in Kvothe's own voice, this is the tale of the magically gifted young man who grows to be the most notorious wizard his world has ever seen...",
        "status": "active",
        "import_source": "mam_scraper",
        "metadata_completeness_percent": 95,
        "abs_id": "li_abc123xyz",
        "created_at": "2025-11-18T14:25:52.863Z",
        "updated_at": "2025-11-18T14:25:52.863Z"
      }
    ],
    "page_info": {
      "page": 1,
      "page_size": 20,
      "total_pages": 25,
      "total_items": 500
    }
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### POST /books

**Description:** Create a new book

**Request Body:**
```json
{
  "title": "The Name of the Wind",
  "author": "Patrick Rothfuss",
  "series": "The Kingkiller Chronicle",
  "series_number": "1",
  "isbn": "9780756404741",
  "asin": "B007978NPG",
  "publisher": "DAW Books",
  "published_year": 2007,
  "duration_minutes": 1260,
  "description": "Told in Kvothe's own voice...",
  "import_source": "manual"
}
```

**Response Example:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "title": "The Name of the Wind",
    "author": "Patrick Rothfuss",
    "status": "active",
    "created_at": "2025-11-18T14:25:52.863Z"
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### GET /books/{book_id}

**Description:** Retrieve detailed information about a specific book

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `book_id` | integer | Yes | Book ID |

**Response Example:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "title": "The Name of the Wind",
    "author": "Patrick Rothfuss",
    "series": "The Kingkiller Chronicle",
    "series_number": "1",
    "isbn": "9780756404741",
    "asin": "B007978NPG",
    "publisher": "DAW Books",
    "published_year": 2007,
    "duration_minutes": 1260,
    "description": "Told in Kvothe's own voice, this is the tale of the magically gifted young man who grows to be the most notorious wizard his world has ever seen. The intimate narrative of his childhood in a troupe of traveling players, his years spent as a near-feral orphan in a crime-ridden city, his daringly brazen yet successful bid to enter a legendary school of magic, and his life as a fugitive after the murder of a king form a gripping coming-of-age story unparalleled in recent literature.",
    "status": "active",
    "import_source": "mam_scraper",
    "metadata_completeness_percent": 95,
    "abs_id": "li_abc123xyz",
    "metadata_source": {
      "title": "google_books",
      "author": "mam_scraper",
      "description": "manual_correction"
    },
    "created_at": "2025-11-18T14:25:52.863Z",
    "updated_at": "2025-11-18T14:25:52.863Z"
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### PUT /books/{book_id}

**Description:** Update book information

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `book_id` | integer | Yes | Book ID |

**Request Body:**
```json
{
  "title": "The Name of the Wind (Updated)",
  "author": "Patrick Rothfuss",
  "description": "Updated description...",
  "status": "active"
}
```

### GET /books/search

**Description:** Search books by query string

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `limit` | integer | No | Maximum results (default: 20, max: 100) |
| `fields` | string | No | Fields to search (title, author, series, description) |

---

## Downloads API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/downloads` | List downloads with filtering |
| `POST` | `/downloads` | Queue new download |
| `GET` | `/downloads/{download_id}` | Get download details |
| `PUT` | `/downloads/{download_id}/status` | Update download status |
| `PUT` | `/downloads/{download_id}/mark-complete` | Mark as completed |
| `PUT` | `/downloads/{download_id}/mark-failed` | Mark as failed |
| `PUT` | `/downloads/{download_id}/retry` | Schedule retry |
| `DELETE` | `/downloads/{download_id}` | Remove download |
| `GET` | `/downloads/pending` | Get pending downloads |
| `GET` | `/downloads/failed` | Get failed downloads |
| `GET` | `/downloads/retry-due` | Get downloads ready for retry |

### GET /downloads

**Description:** Retrieve list of downloads with optional status filtering

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status (queued, downloading, completed, failed, abandoned) |
| `source` | string | No | Filter by source (MAM, GoogleBooks, Goodreads, Manual) |
| `limit` | integer | No | Maximum results (default: 100) |
| `offset` | integer | No | Offset for pagination |
| `sort_by` | string | No | Sort field (created_at, updated_at, status) |
| `sort_order` | string | No | Sort direction (asc, desc) |

**Response Example:**
```json
{
  "success": true,
  "data": {
    "downloads": [
      {
        "id": 456,
        "book_id": 123,
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "source": "MAM",
        "status": "downloading",
        "progress_percent": 67,
        "qb_hash": "abc123def456",
        "qb_status": "downloading",
        "download_speed_bps": 2048576,
        "upload_speed_bps": 51200,
        "eta_seconds": 7200,
        "retry_count": 0,
        "max_retries": 3,
        "created_at": "2025-11-18T14:25:52.863Z",
        "updated_at": "2025-11-18T14:25:52.863Z",
        "completed_at": null,
        "failed_at": null
      }
    ],
    "total": 1,
    "has_more": false
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### POST /downloads

**Description:** Queue a new download

**Request Body:**
```json
{
  "book_id": 123,
  "title": "The Name of the Wind",
  "author": "Patrick Rothfuss",
  "source": "MAM",
  "magnet_link": "magnet:?xt=urn:btih:abc123def456",
  "torrent_url": "https://example.com/torrent/file.torrent"
}
```

### PUT /downloads/{download_id}/status

**Description:** Update download status

**Request Body:**
```json
{
  "status": "downloading",
  "qb_hash": "abc123def456",
  "qb_status": "downloading"
}
```

---

## System API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/system/health` | Health check (public) |
| `GET` | `/system/stats` | System statistics |
| `GET` | `/system/library-status` | Library health status |
| `GET` | `/system/download-stats` | Download statistics |
| `GET` | `/system/storage` | Storage usage statistics |
| `POST` | `/system/trigger-full-scan` | Trigger full system scan |
| `GET` | `/system/configuration` | System configuration |
| `POST` | `/system/logs/export` | Export system logs |

### GET /system/health

**Description:** Comprehensive health check (public endpoint)

**Response Example:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-11-18T14:25:52.863Z",
    "components": {
      "database": {
        "status": "healthy",
        "response_time_ms": 12,
        "connections_active": 5,
        "connections_total": 20
      },
      "scheduler": {
        "status": "healthy",
        "last_run": "2025-11-18T13:00:00.000Z",
        "next_run": "2025-11-18T15:00:00.000Z",
        "active_jobs": 3
      },
      "qbittorrent": {
        "status": "healthy",
        "version": "4.6.5",
        "active_downloads": 2,
        "total_downloads": 156
      },
      "audiobookshelf": {
        "status": "healthy",
        "version": "2.8.1",
        "libraries": 1,
        "total_books": 1247
      }
    },
    "uptime_seconds": 86400,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 15.2
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### GET /system/stats

**Description:** System-wide statistics

**Response Example:**
```json
{
  "success": true,
  "data": {
    "books": {
      "grand_total": 1247,
      "total_active": 1156,
      "total_archived": 45,
      "total_duplicates": 46
    },
    "series": {
      "total": 234,
      "complete": 89,
      "partial": 98,
      "incomplete": 47
    },
    "authors": {
      "total": 567,
      "with_multiple_books": 234
    },
    "downloads": {
      "total": 1245,
      "completed": 1156,
      "failed": 67,
      "pending": 22,
      "success_rate_percent": 94.6
    },
    "metadata": {
      "average_completeness_percent": 87.3,
      "books_100_percent": 567,
      "books_below_80_percent": 123
    },
    "storage": {
      "estimated_audiobook_storage_gb": 2156,
      "database_size_mb": 245,
      "logs_size_mb": 67
    }
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

---

## Series API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/series` | List series with filtering |
| `POST` | `/series` | Create new series |
| `GET` | `/series/{series_id}` | Get series details |
| `PUT` | `/series/{series_id}` | Update series |
| `DELETE` | `/series/{series_id}` | Delete series |
| `GET` | `/series/{series_id}/books` | Get books in series |

---

## Authors API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/authors` | List authors with filtering |
| `POST` | `/authors` | Create new author |
| `GET` | `/authors/{author_id}` | Get author details |
| `PUT` | `/authors/{author_id}` | Update author |
| `DELETE` | `/authors/{author_id}` | Delete author |
| `GET` | `/authors/{author_id}/books` | Get books by author |

---

## Metadata API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/metadata/correct` | Submit metadata correction |
| `GET` | `/metadata/corrections` | List pending corrections |
| `PUT` | `/metadata/corrections/{correction_id}` | Update correction status |
| `POST` | `/metadata/validate` | Validate metadata for book |
| `GET` | `/metadata/sources` | List available metadata sources |

---

## Scheduler API

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scheduler/jobs` | List scheduled jobs |
| `POST` | `/scheduler/jobs` | Create new job |
| `PUT` | `/scheduler/jobs/{job_id}` | Update job |
| `DELETE` | `/scheduler/jobs/{job_id}` | Delete job |
| `POST` | `/scheduler/jobs/{job_id}/trigger` | Trigger job immediately |

---

## Admin API

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/auth/login` | Admin login |
| `POST` | `/admin/auth/logout` | Admin logout |
| `POST` | `/admin/auth/refresh` | Refresh JWT token |

### Management Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/users` | List users |
| `POST` | `/admin/users` | Create user |
| `PUT` | `/admin/users/{user_id}` | Update user |
| `DELETE` | `/admin/users/{user_id}` | Delete user |
| `GET` | `/admin/config` | Get system configuration |
| `PUT` | `/admin/config` | Update system configuration |

---

## Real-time Updates

### WebSocket Connection
Connect to real-time updates using WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Authentication
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }));
};

// Subscribe to updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['downloads', 'books', 'system']
}));

// Handle updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update received:', data);
};
```

### WebSocket Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `download_updated` | Download status changed | `{id, status, progress}` |
| `book_created` | New book added | `{id, title, author}` |
| `book_updated` | Book metadata changed | `{id, changes}` |
| `system_status` | System health changed | `{component, status}` |
| `crawler_started` | Crawler job started | `{job_type, started_at}` |
| `crawler_completed` | Crawler job finished | `{job_type, results}` |

---

## WebSocket Endpoints

### Base WebSocket URL
```
ws://localhost:8000/ws
```

### Authentication
WebSocket connections require JWT token authentication:

```javascript
{
  "type": "auth",
  "token": "your-jwt-token-here"
}
```

### Subscriptions
Subscribe to real-time updates:

```javascript
{
  "type": "subscribe",
  "channels": [
    "downloads",     // Download status updates
    "books",        // Book creation/updates
    "system",       // System health updates
    "scheduler",    // Scheduler job updates
    "metadata"      // Metadata correction updates
  ]
}
```

### Message Format
All WebSocket messages follow this format:

```json
{
  "type": "event_type",
  "channel": "channel_name",
  "data": {
    // Event-specific data
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

### Event Types

#### Download Updates
```json
{
  "type": "download_updated",
  "channel": "downloads",
  "data": {
    "id": 456,
    "status": "downloading",
    "progress_percent": 67,
    "download_speed_bps": 2048576,
    "eta_seconds": 7200
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

#### Book Updates
```json
{
  "type": "book_updated",
  "channel": "books",
  "data": {
    "id": 123,
    "title": "The Name of the Wind",
    "changes": {
      "description": "Updated description..."
    },
    "updated_by": "user_123"
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

#### System Status
```json
{
  "type": "system_status",
  "channel": "system",
  "data": {
    "component": "database",
    "status": "degraded",
    "response_time_ms": 500,
    "message": "High connection count"
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

---

## Security Considerations

### API Key Security
- Store API keys securely (environment variables, key management systems)
- Rotate API keys regularly
- Use different keys for development, staging, and production
- Monitor API key usage for anomalies

### Authentication
- JWT tokens have a 30-minute expiration for admin sessions
- Implement proper session management
- Use HTTPS in production
- Implement proper CORS policies

### Input Validation
- All inputs are validated using Pydantic schemas
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention through proper HTML escaping
- File upload restrictions and validation

### Rate Limiting
- API endpoints are rate limited to prevent abuse
- Limit: 1000 requests per hour per API key
- Limit: 100 requests per minute for search endpoints
- Excess requests return HTTP 429 with retry information

### Data Protection
- Sensitive data is encrypted at rest
- Database connections use SSL/TLS
- Log sanitization to prevent sensitive data exposure
- Regular security audits and updates

---

## Rate Limiting

### Rate Limits by Endpoint Type
| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| General API | 1000 requests | 1 hour |
| Search | 100 requests | 1 minute |
| Bulk Operations | 50 requests | 1 hour |
| Admin Operations | 500 requests | 1 hour |
| WebSocket | 1 connection | Per API key |

### Rate Limit Headers
Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1634567890
X-RateLimit-Window: 3600
```

### Rate Limit Exceeded Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 300 seconds.",
    "retry_after": 300
  },
  "timestamp": "2025-11-18T14:25:52.863Z"
}
```

---

## Code Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

class MAMcrawlerAPI {
  constructor(baseURL, apiKey) {
    this.client = axios.create({
      baseURL,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json'
      }
    });
  }

  async getBooks(options = {}) {
    const params = new URLSearchParams({
      page: options.page || 1,
      page_size: options.pageSize || 50,
      ...options.filters
    });
    
    const response = await this.client.get(`/books?${params}`);
    return response.data.data;
  }

  async createBook(bookData) {
    const response = await this.client.post('/books', bookData);
    return response.data.data;
  }

  async searchBooks(query, limit = 20) {
    const response = await this.client.get('/books/search', {
      params: { q: query, limit }
    });
    return response.data.data;
  }

  async getDownloads(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await this.client.get(`/downloads?${params}`);
    return response.data.data;
  }

  async updateDownloadStatus(downloadId, status, extraData = {}) {
    const response = await this.client.put(`/downloads/${downloadId}/status`, {
      status,
      ...extraData
    });
    return response.data.data;
  }

  async getSystemStats() {
    const response = await this.client.get('/system/stats');
    return response.data.data;
  }

  connectWebSocket(jwtToken) {
    const ws = new WebSocket(`ws://localhost:8000/ws`);
    
    ws.onopen = () => {
      // Authenticate
      ws.send(JSON.stringify({
        type: 'auth',
        token: jwtToken
      }));
      
      // Subscribe to updates
      ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['downloads', 'books', 'system']
      }));
    };
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      this.handleWebSocketUpdate(update);
    };
    
    return ws;
  }

  handleWebSocketUpdate(update) {
    switch (update.type) {
      case 'download_updated':
        console.log(`Download ${update.data.id} status: ${update.data.status}`);
        break;
      case 'book_updated':
        console.log(`Book ${update.data.id} updated`);
        break;
      case 'system_status':
        console.log(`System component ${update.data.component} status: ${update.data.status}`);
        break;
    }
  }
}

// Usage example
async function main() {
  const api = new MAMcrawlerAPI('http://localhost:8000/api', 'your-api-key');
  
  // Get books
  const books = await api.getBooks({
    page: 1,
    pageSize: 20,
    filters: {
      status: 'active',
      search: 'wind'
    }
  });
  
  console.log(`Found ${books.books.length} books`);
  
  // Create new book
  const newBook = await api.createBook({
    title: 'New Book Title',
    author: 'Author Name',
    series: 'Series Name',
    series_number: '1'
  });
  
  console.log(`Created book with ID: ${newBook.id}`);
  
  // Monitor real-time updates
  const ws = api.connectWebSocket('your-jwt-token');
}
```

### Python

```python
import requests
import websocket
import json
from typing import Optional, Dict, Any, List

class MAMcrawlerAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_books(self, page: int = 1, page_size: int = 50, **filters) -> Dict[str, Any]:
        """Get books with optional filtering"""
        params = {
            'page': page,
            'page_size': page_size,
            **filters
        }
        
        response = requests.get(
            f"{self.base_url}/books",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()['data']
    
    def create_book(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new book"""
        response = requests.post(
            f"{self.base_url}/books",
            headers=self.headers,
            json=book_data
        )
        response.raise_for_status()
        return response.json()['data']
    
    def search_books(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search books by query"""
        response = requests.get(
            f"{self.base_url}/books/search",
            headers=self.headers,
            params={'q': query, 'limit': limit}
        )
        response.raise_for_status()
        return response.json()['data']['books']
    
    def get_downloads(self, **filters) -> Dict[str, Any]:
        """Get downloads with optional filtering"""
        response = requests.get(
            f"{self.base_url}/downloads",
            headers=self.headers,
            params=filters
        )
        response.raise_for_status()
        return response.json()['data']
    
    def update_download_status(self, download_id: int, status: str, **extra_data) -> Dict[str, Any]:
        """Update download status"""
        response = requests.put(
            f"{self.base_url}/downloads/{download_id}/status",
            headers=self.headers,
            json={'status': status, **extra_data}
        )
        response.raise_for_status()
        return response.json()['data']
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        response = requests.get(
            f"{self.base_url}/system/stats",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['data']
    
    def connect_websocket(self, jwt_token: str):
        """Connect to WebSocket for real-time updates"""
        def on_message(ws, message):
            update = json.loads(message)
            self._handle_websocket_update(update)
        
        def on_open(ws):
            # Authenticate
            ws.send(json.dumps({
                'type': 'auth',
                'token': jwt_token
            }))
            
            # Subscribe to updates
            ws.send(json.dumps({
                'type': 'subscribe',
                'channels': ['downloads', 'books', 'system']
            }))
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        ws_url = self.base_url.replace('http', 'ws') + '/ws'
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open,
            on_error=on_error
        )
        return self.ws
    
    def _handle_websocket_update(self, update: Dict[str, Any]):
        """Handle incoming WebSocket updates"""
        update_type = update.get('type')
        data = update.get('data')
        
        if update_type == 'download_updated':
            print(f"Download {data['id']} status: {data['status']}")
        elif update_type == 'book_updated':
            print(f"Book {data['id']} updated")
        elif update_type == 'system_status':
            print(f"System component {data['component']} status: {data['status']}")

# Usage example
async def main():
    api = MAMcrawlerAPI('http://localhost:8000/api', 'your-api-key')
    
    # Get books
    books = api.get_books(page=1, page_size=20, status='active', search='wind')
    print(f"Found {len(books['books'])} books")
    
    # Create new book
    new_book = api.create_book({
        'title': 'New Book Title',
        'author': 'Author Name',
        'series': 'Series Name',
        'series_number': '1'
    })
    print(f"Created book with ID: {new_book['id']}")
    
    # Search books
    search_results = api.search_books('Patrick Rothfuss', limit=10)
    print(f"Search found {len(search_results)} books")
    
    # Get downloads
    downloads = api.get_downloads(status='downloading')
    print(f"Active downloads: {len(downloads['downloads'])}")
    
    # Get system stats
    stats = api.get_system_stats()
    print(f"Total books: {stats['books']['grand_total']}")
    
    # Connect to WebSocket for real-time updates
    ws = api.connect_websocket('your-jwt-token')
    ws.run_forever()

if __name__ == '__main__':
    main()
```

### cURL Examples

#### Get Books
```bash
curl -X GET "http://localhost:8000/api/books?page=1&page_size=20&status=active" \
  -H "X-API-Key: your-secret-api-key"
```

#### Create Book
```bash
curl -X POST "http://localhost:8000/api/books" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Name of the Wind",
    "author": "Patrick Rothfuss",
    "series": "The Kingkiller Chronicle",
    "series_number": "1",
    "isbn": "9780756404741"
  }'
```

#### Update Book
```bash
curl -X PUT "http://localhost:8000/api/books/123" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Name of the Wind (Updated)",
    "description": "Updated description..."
  }'
```

#### Get Downloads
```bash
curl -X GET "http://localhost:8000/api/downloads?status=downloading&limit=10" \
  -H "X-API-Key: your-secret-api-key"
```

#### Queue Download
```bash
curl -X POST "http://localhost:8000/api/downloads" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 123,
    "title": "The Name of the Wind",
    "author": "Patrick Rothfuss",
    "source": "MAM",
    "magnet_link": "magnet:?xt=urn:btih:abc123def456"
  }'
```

#### Get System Stats
```bash
curl -X GET "http://localhost:8000/api/system/stats" \
  -H "X-API-Key: your-secret-api-key"
```

#### Health Check
```bash
curl -X GET "http://localhost:8000/api/system/health"
```

#### Admin Login
```bash
curl -X POST "http://localhost:8000/api/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

---

## Testing

### Postman Collection
Import the following Postman collection to test the API:

```json
{
  "info": {
    "name": "MAMcrawler API",
    "description": "Complete API collection for MAMcrawler",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "apikey",
    "apikey": [
      {
        "key": "value",
        "value": "your-secret-api-key",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api"
    }
  ]
}
```

### API Testing with curl
```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api"
API_KEY="your-secret-api-key"

# Test health endpoint
echo "Testing health endpoint..."
curl -s "$BASE_URL/system/health" | jq .

# Test books endpoint
echo "Testing books endpoint..."
curl -s -X GET "$BASE_URL/books?page=1&page_size=5" \
  -H "X-API-Key: $API_KEY" | jq .

# Test search endpoint
echo "Testing search endpoint..."
curl -s -X GET "$BASE_URL/books/search?q=wind&limit=5" \
  -H "X-API-Key: $API_KEY" | jq .

# Test system stats
echo "Testing system stats..."
curl -s -X GET "$BASE_URL/system/stats" \
  -H "X-API-Key: $API_KEY" | jq .
```

---

## Changelog

### Version 1.0.0 (2025-11-18)
- Initial API release
- Books CRUD operations
- Downloads management
- System statistics
- WebSocket real-time updates
- JWT authentication for admin panel
- Comprehensive filtering and pagination
- Rate limiting and security measures

---

## Support

For API support and questions:
- Documentation: This file
- Issues: Create an issue in the project repository
- Email: support@mamcrawler.example.com

---

*Last updated: 2025-11-18T14:25:52.863Z*