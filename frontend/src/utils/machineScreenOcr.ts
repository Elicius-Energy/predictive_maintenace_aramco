import axios from 'axios';

export interface MachineScreenExtracted {
  machine_make?: string | null;
  machine_name?: string | null;
  machine_model_no?: string | null;
  shift?: string | null;
  screen_date?: string | null;
  screen_time?: string | null;
  count_ne?: number | null;
  spindle_rpm?: number | null;
  chase_mm?: number | null;
  length_m?: number | null;
  doff_time_min?: number | null;
  front_roller_rpm?: number | null;
  tpi?: number | null;
  delivery_speed_m_min?: number | null;
  efficiency_pct?: number | null;
  suction_pressure_mm_wc?: number | null;
  machine_status?: string | null;
  uploaded_at?: string | null;
  ts?: string | null;
}

export interface MachineScreenOcrResponse {
  success: boolean;
  partial?: boolean;
  needs_reupload?: boolean;
  confidence?: string;
  unclear_fields?: string[];
  reason?: string;
  device_id?: string;
  matched_timestamp?: string | null;
  matched_timestamp_ist?: string | null;
  extracted: MachineScreenExtracted;
  profile_updated?: Record<string, any>;
  message?: string;
}

/**
 * Downscales an image file in memory (max 1280px, JPEG 0.85) and immediately
 * frees the object URL and canvas buffer so zero image memory is retained.
 */
export async function compressImageToBase64(file: File): Promise<{ base64: string; mimeType: string }> {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      try {
        const maxDim = 1600;
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;
        if (width > maxDim || height > maxDim) {
          if (width >= height) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          } else {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('Could not initialize image canvas context');
        }
        ctx.drawImage(img, 0, 0, width, height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.90);
        // Immediately release canvas memory
        canvas.width = 0;
        canvas.height = 0;
        URL.revokeObjectURL(objectUrl);
        const base64 = dataUrl.includes(',') ? dataUrl.split(',', 2)[1] : dataUrl;
        resolve({ base64, mimeType: 'image/jpeg' });
      } catch (err) {
        URL.revokeObjectURL(objectUrl);
        reject(err);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Failed to read image file. Please select a valid photo.'));
    };
    img.src = objectUrl;
  });
}

export async function uploadMachineScreenImage(
  deviceId: string,
  file: File,
  targetTimeIso?: string
): Promise<MachineScreenOcrResponse> {
  let { base64, mimeType } = await compressImageToBase64(file);
  try {
    const csrf = document.cookie
      .split('; ')
      .find((part) => part.startsWith('elicius_csrf='))
      ?.split('=')[1];

    const res = await axios.post<MachineScreenOcrResponse>(
      `/api/devices/${deviceId}/upload-machine-screen`,
      {
        image_base64: base64,
        mime_type: mimeType,
        target_time: targetTimeIso || new Date().toISOString(),
      },
      {
        withCredentials: true,
        headers: csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {},
      }
    );
    return res.data;
  } finally {
    // Release string reference immediately after request completes
    base64 = '';
  }
}
