# SSL Certificates

This directory should contain your SSL certificates for HTTPS.

## Required Files
- `server.crt` - SSL certificate file
- `server.key` - SSL private key file

## For Development
For local development, you can generate self-signed certificates:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key \
  -out server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## For Production
Use certificates from a trusted Certificate Authority (CA) like:
- Let's Encrypt (free)
- DigiCert
- Comodo
- GlobalSign

## Security Notes
- Never commit private keys to version control
- Keep `.key` files secure with proper permissions (600)
- Use strong encryption (2048-bit RSA or higher)
- Renew certificates before expiration
