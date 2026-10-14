import { useEffect, useId, useRef } from "react";
import { Html5QrcodeScanner, Html5QrcodeScanType, Html5QrcodeSupportedFormats } from "html5-qrcode";

export default function EmergencyQrScanner({ onScan }) {
  const reactId = useId();
  const elementId = `emergency-qr-reader-${reactId.replaceAll(":", "")}`;
  const onScanRef = useRef(onScan);
  onScanRef.current = onScan;

  useEffect(() => {
    const scanner = new Html5QrcodeScanner(
      elementId,
      {
        fps: 10,
        qrbox: { width: 240, height: 240 },
        formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
        supportedScanTypes: [
          Html5QrcodeScanType.SCAN_TYPE_CAMERA,
          Html5QrcodeScanType.SCAN_TYPE_FILE
        ]
      },
      false
    );
    scanner.render((decodedText) => onScanRef.current(decodedText), undefined);
    return () => {
      scanner.clear().catch((error) => {
        console.error("Could not stop the emergency QR scanner cleanly.", error);
      });
    };
  }, [elementId]);

  return <div id={elementId} className="qr-scanner-shell" aria-label="Emergency contact QR scanner" />;
}
