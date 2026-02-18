# Rate Limiting Policy

To ensure system stability and fair usage, the Seismic Internal API enforces rate limits on all endpoints.

## Standard Limits
By default, all authenticated users are subject to the following rate limits:
- **100 requests per minute.**
- **1,000 requests per hour.**

Exceeding these limits will result in a `429 Too Many Requests` error response. The response headers will include `X-RateLimit-Limit` (the total limit), `X-RateLimit-Remaining` (requests remaining in the current window), and `X-RateLimit-Reset` (a UTC timestamp for when the limit resets).

## Enterprise Tier
Clients on the Enterprise plan have an increased rate limit of **500 requests per minute**. To upgrade your plan, please contact the support team. There are no other tiers available at this time.

