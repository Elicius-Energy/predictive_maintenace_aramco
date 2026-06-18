import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

export const generatePdfFromElement = async (
  element: HTMLElement | null,
  fileName: string
) => {
  if (!element) return;

  try {
    // Temporarily make the element visible for capture if it was hidden
    const originalStyle = element.style.cssText;
    element.style.position = 'absolute';
    element.style.left = '0';
    element.style.top = '0';
    element.style.opacity = '1';
    element.style.zIndex = '-9999';

    // Wait for browser layout to update
    await new Promise(resolve => setTimeout(resolve, 200));

    const canvas = await html2canvas(element, {
      scale: 2, // High resolution
      useCORS: true,
      logging: false,
      windowWidth: 800
    });

    // Restore original styles
    element.style.cssText = originalStyle;

    const imgData = canvas.toDataURL('image/jpeg', 0.95);
    
    // Calculate pages
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'px',
      format: 'a4'
    });

    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = canvas.width;
    const imgHeight = canvas.height;
    const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
    
    // Because the template is long, we'll want to split it by A4 page heights
    const pageHeightInPixels = pdfHeight / (pdfWidth / imgWidth);
    let heightLeft = imgHeight;
    let position = 0;

    pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeight * (pdfWidth / imgWidth));
    heightLeft -= pageHeightInPixels;

    while (heightLeft > 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'JPEG', 0, position * (pdfWidth / imgWidth), pdfWidth, imgHeight * (pdfWidth / imgWidth));
      heightLeft -= pageHeightInPixels;
    }

    pdf.save(fileName);
  } catch (error: any) {
    console.error('Error generating PDF:', error);
    alert(`Failed to generate PDF: ${error.message || String(error)}`);
  }
};
