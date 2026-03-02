# NSFW Guard Pro API Documentation

Welcome to the NSFW Guard Pro API. This service provides advanced, local AI-powered image analysis and intelligent censorship.

## Security & Privacy

*   **100% Local**: No images are ever sent to external cloud services.
*   **API Key**: All requests must include the `X-API-KEY` header.
*   **File Size**: Maximum **10MB** per image file (configurable in `backend/app.py`).
*   **Concurrency**: Global limit of **2** simultaneous heavy AI processing tasks to preserve system stability.

---

## Authentication

All API requests require an `X-API-KEY` header.

*   **Header Name**: `X-API-KEY`
*   **Default Key**: `NSFW_PRO_8rqNo38SzYgZX86-byPnlZvvXzpiJL5rbE_TYIkbce8`
*   **Configuration**: Change this by setting the `NSFW_API_KEY` environment variable before starting the server.

---

## Endpoints

### 1. Process Image (File Upload)

Analyze and censor a single image file.

*   **URL**: `/api/process`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | File | Yes | The image file (JPG, PNG, WEBP). |
| `mode` | String | No | `blur` (default), `pixel`, or `solid`. |
| `intensity` | Integer | No | Intensity of effect (11-151). Default: 91. |
| `color` | String | No | Hex color for `solid` mode (e.g., `#FFC0CB`). Default: `#000000`. |

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/process \
  -H "X-API-KEY: your_api_key_here" \
  -F "file=@image.jpg" \
  -F "mode=blur" \
  -F "intensity=91"
```

### 2. Process Batch (Multi-file Upload)

Analyze and censor multiple images in a single request. 

*   **URL**: `/api/process-batch`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `files` | File[] | Yes | Array of image files. |
| `mode` | String | No | `blur`, `pixel`, or `solid`. |
| `intensity` | Integer | No | Intensity of effect. |

**Response**: Returns an object with a `results` array containing individual process objects.

---

### 3. Process Image (Base64 JSON)

Analyze and censor an image provided as a Base64 string.

*   **URL**: `/api/process-base64`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

**Request Body (JSON):**

```json
{
  "image": "data:image/jpeg;base64,...",
  "mode": "blur",
  "intensity": 91,
  "color": "#000000",
  "return_base64": true
}
```

*   `return_base64`: If `true`, returns the processed image as a Base64 string in the JSON response.

---

## Response Format

All endpoints return a JSON object:

```json
{
  "id": "uuid-string",
  "scores": [
    { "label": "porn", "score": 0.98 },
    { "label": "neutral", "score": 0.02 }
  ],
  "detections": [
    { "label": "FEMALE_BREAST_EXPOSED", "score": 0.95, "box": [x, y, w, h] }
  ],
  "blur_count": 2,
  "processed_url": "/api/files/processed_uuid.jpg"
}
```

---

## Error Codes

| Code | Meaning |
| :--- | :--- |
| **403** | Invalid or missing `X-API-KEY`. |
| **413** | File size exceeds the 10MB limit. |
| **422** | Unprocessable Entity (missing required fields). |
| **500** | AI engine error or file write failure. |
