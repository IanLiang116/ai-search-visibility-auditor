const PAYMENT_URL = "";
const PAYMENT_QR_IMAGE = "payment-qr.png";

function activatePaymentLinks() {
  const links = [document.getElementById("buyLink"), document.getElementById("heroBuyLink")];
  const paymentNote = document.getElementById("paymentNote");
  const qrPanel = document.getElementById("qrPanel");
  const paymentQr = document.getElementById("paymentQr");

  if (PAYMENT_URL) {
    links.forEach((link) => {
      if (!link) return;
      link.href = PAYMENT_URL;
      link.removeAttribute("aria-disabled");
      link.textContent = "Buy for $1";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    });

    if (paymentNote) {
      paymentNote.textContent = "Checkout opens in a new tab. Delivery is handled through your payment provider.";
    }

    return;
  }

  if (!qrPanel || !paymentQr) {
    return;
  }

  const probe = new Image();
  probe.onload = () => {
    qrPanel.hidden = false;
    paymentQr.src = PAYMENT_QR_IMAGE;

    links.forEach((link) => {
      if (!link) return;
      link.href = "#buy";
      link.removeAttribute("aria-disabled");
      link.textContent = "Scan QR to pay $1";
      link.removeAttribute("target");
      link.removeAttribute("rel");
    });

    if (paymentNote) {
      paymentNote.textContent = "$1 suggested price. Immediate download is available so buyers do not need to wait for manual delivery.";
    }
  };
  probe.src = PAYMENT_QR_IMAGE;
}

activatePaymentLinks();
