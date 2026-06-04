# $1 AI Micro-SaaS Idea Pack

A tiny static landing page built to test one goal: make a first $1 sale.

## Product

The offer is an honor-system $1 digital idea pack for solo builders who are stuck choosing what to build.

The deliverable is `idea-pack.md`, linked directly from the page to reduce purchase friction.

## Payment Link

Before deploying, add either a checkout URL or a QR code.

For a checkout URL, edit `script.js`:

```js
const PAYMENT_URL = "https://your-payment-link.example";
```

For a QR code, add the image file here:

```text
payment-qr.png
```

If both are present, the checkout URL is used first. If only `payment-qr.png` is present, the page displays the QR payment block.

For privacy, use a cropped QR image that does not include the recipient name or surrounding payment-card text. PayPal may still show recipient details on its own checkout screen.

Recommended payment providers:

- Gumroad
- Ko-fi
- PayPal.me
- Stripe Payment Links
- Tally form with Stripe payment enabled

## Deploy

This is a static site. You can deploy it with Vercel, Netlify, GitHub Pages, or any static host.

For Vercel:

1. Push this repository to GitHub.
2. Import the repo in Vercel.
3. Use the project root as the output.
4. No build command is required.

`vercel.json` is included only for clean static URLs. It does not add any backend or paid infrastructure.

## First Sale Workflow

1. Create a $1 checkout link with a payment provider.
2. Paste it into `script.js` as `PAYMENT_URL`, or add your QR code as `payment-qr.png`.
3. Deploy the site.
4. Post one message from `launch-copy.md`.
5. Buyers can download `idea-pack.md` immediately. The $1 payment is honor-system to maximize speed and reduce manual delivery friction.

## Local Preview

Open `index.html` directly in a browser, or run a small local server:

```powershell
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```
