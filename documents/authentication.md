# API Authentication Guide

## Overview
All access to the Seismic Internal API requires authentication. We use an API Key-based system for simplicity and security. Unauthorized requests will result in a `401 Unauthorized` error.

## Generating an API Key
To generate an API key, navigate to your user profile in the internal dashboard and click "Generate New API Key." You must give the key a descriptive name to help you identify it later. Store this key securely, as it will not be shown again.

## Using the API Key
To authenticate your requests, you must include the API key in the request headers. The key should be passed in the `X-API-KEY` header.

Example request using cURL:
```bash
curl -X GET "https://api.internal.seismic.com/v1/status" \
     -H "X-API-KEY: your_secret_api_key_here"
```

Do not expose your API key in client-side code or commit it to version control.

