/**
 * SVG-to-PNG export for chart components.
 */

/**
 * Convert an SVG element to a PNG blob.
 * Clones the SVG, adds a background, and renders via canvas.
 */
export function svgToPng(
  svg: SVGSVGElement,
  scale = 2,
  bgColor = "#0d0d1a",
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const clone = svg.cloneNode(true) as SVGSVGElement;

    // Add background rect as first child
    const bgRect = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "rect",
    );
    bgRect.setAttribute("width", "100%");
    bgRect.setAttribute("height", "100%");
    bgRect.setAttribute("fill", bgColor);
    clone.insertBefore(bgRect, clone.firstChild);

    // Ensure the clone has explicit width/height for the Image
    const bbox = svg.getBoundingClientRect();
    const w = Math.round(bbox.width);
    const h = Math.round(bbox.height);
    clone.setAttribute("width", String(w));
    clone.setAttribute("height", String(h));

    const serializer = new XMLSerializer();
    const svgStr = serializer.serializeToString(clone);
    const svgBlob = new Blob([svgStr], {
      type: "image/svg+xml;charset=utf-8",
    });
    const url = URL.createObjectURL(svgBlob);

    const canvas = document.createElement("canvas");
    canvas.width = w * scale;
    canvas.height = h * scale;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      URL.revokeObjectURL(url);
      reject(new Error("Canvas context not available"));
      return;
    }

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(url);
        if (blob) resolve(blob);
        else reject(new Error("Failed to create PNG"));
      }, "image/png");
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to render SVG as image"));
    };
    img.src = url;
  });
}

/**
 * Trigger a browser download for a Blob.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Find the first SVG inside a container element, convert to PNG, and download.
 * Returns true on success, false if no SVG found or export failed.
 */
export async function exportChartPng(
  container: HTMLElement,
  filename: string,
): Promise<boolean> {
  const svg = container.querySelector("svg");
  if (!svg) return false;
  try {
    const blob = await svgToPng(svg as SVGSVGElement);
    downloadBlob(blob, filename);
    return true;
  } catch {
    return false;
  }
}
