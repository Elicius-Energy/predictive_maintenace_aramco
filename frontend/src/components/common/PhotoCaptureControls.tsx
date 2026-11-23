import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Camera, Upload, Loader2, X, Aperture, AlertCircle } from 'lucide-react';

interface PhotoCaptureControlsProps {
  /** Short label, e.g. "Machine Screen" or "Motor Nameplate" */
  label: string;
  /** Shown while OCR request is in flight */
  loading?: boolean;
  loadingLabel?: string;
  /** Color theme for the button group */
  variant?: 'indigo' | 'teal';
  /** Called with the selected or captured image File */
  onFileSelected: (file: File) => void;
  /** Optional tooltip */
  title?: string;
  /** Optional imperative handle refs to trigger upload or camera from outside (e.g. re-upload modal) */
  uploadTriggerRef?: React.MutableRefObject<(() => void) | null>;
  cameraTriggerRef?: React.MutableRefObject<(() => void) | null>;
}

const isMobileOrTablet = (): boolean => {
  if (typeof window === 'undefined') return false;
  const ua = navigator.userAgent || '';
  const touchCoarse = typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;
  return /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(ua) || touchCoarse;
};

export const PhotoCaptureControls: React.FC<PhotoCaptureControlsProps> = ({
  label,
  loading = false,
  loadingLabel,
  variant = 'indigo',
  onFileSelected,
  title,
  uploadTriggerRef,
  cameraTriggerRef,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const nativeCameraInputRef = useRef<HTMLInputElement | null>(null);

  // Desktop / WebRTC live camera modal state
  const [cameraModalOpen, setCameraModalOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCameraStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraReady(false);
  }, []);

  const closeCameraModal = useCallback(() => {
    stopCameraStream();
    setCameraModalOpen(false);
    setCameraError(null);
  }, [stopCameraStream]);

  useEffect(() => {
    return () => {
      stopCameraStream();
    };
  }, [stopCameraStream]);

  const openLiveCamera = useCallback(async () => {
    // On phones & tablets, use the native OS camera capture input (better focus, zoom, flash)
    if (isMobileOrTablet()) {
      nativeCameraInputRef.current?.click();
      return;
    }

    // On desktop/laptop, open live camera preview modal if getUserMedia is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      nativeCameraInputRef.current?.click();
      return;
    }

    setCameraError(null);
    setCameraReady(false);
    setCameraModalOpen(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1600 },
          height: { ideal: 1200 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraReady(true);
      }
    } catch (err: any) {
      stopCameraStream();
      setCameraError(
        err?.name === 'NotAllowedError'
          ? 'Camera permission was denied. Please allow camera access or choose an image file instead.'
          : 'Could not access the camera on this device. You can upload an image file instead.'
      );
    }
  }, [stopCameraStream]);

  // Expose imperative triggers for parent modals (e.g. "Re-upload" / "Retake")
  useEffect(() => {
    if (uploadTriggerRef) {
      uploadTriggerRef.current = () => fileInputRef.current?.click();
    }
    if (cameraTriggerRef) {
      cameraTriggerRef.current = () => {
        void openLiveCamera();
      };
    }
  }, [uploadTriggerRef, cameraTriggerRef, openLiveCamera]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Immediately clear input so browser does not retain image memory
    e.target.value = '';
    if (!file) return;
    onFileSelected(file);
  };

  const handleCaptureFrame = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        canvas.width = 0;
        canvas.height = 0;
        closeCameraModal();
        if (blob) {
          const capturedFile = new File([blob], `${label.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}.jpg`, {
            type: 'image/jpeg',
          });
          onFileSelected(capturedFile);
        }
      },
      'image/jpeg',
      0.92
    );
  };

  const theme =
    variant === 'teal'
      ? {
          primary: 'bg-teal-600 hover:bg-teal-700 text-white',
          secondary: 'bg-teal-700 hover:bg-teal-800 text-white border-l border-teal-500/50',
        }
      : {
          primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
          secondary: 'bg-indigo-700 hover:bg-indigo-800 text-white border-l border-indigo-500/50',
        };

  return (
    <>
      {/* Hidden standard file picker */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleInputChange}
        className="hidden"
      />

      {/* Hidden native mobile camera input */}
      <input
        ref={nativeCameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleInputChange}
        className="hidden"
      />

      {/* Compact Split Button: Upload + Take Photo */}
      <div
        className="inline-flex items-stretch rounded-lg overflow-hidden shadow-xs"
        title={title}
      >
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold transition-colors cursor-pointer disabled:opacity-50 ${theme.primary}`}
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
          ) : (
            <Upload className="w-3.5 h-3.5 shrink-0" />
          )}
          <span>{loading ? (loadingLabel || `Reading ${label}...`) : label}</span>
        </button>

        <button
          type="button"
          onClick={openLiveCamera}
          disabled={loading}
          title={`Take photo of ${label} with camera`}
          aria-label={`Take photo of ${label}`}
          className={`flex items-center gap-1 px-2.5 py-1.5 text-xs font-bold transition-colors cursor-pointer disabled:opacity-50 ${theme.secondary}`}
        >
          <Camera className="w-3.5 h-3.5 shrink-0" />
          <span className="hidden sm:inline">Photo</span>
        </button>
      </div>

      {/* Live Camera Capture Modal (Desktop / Laptop) */}
      {cameraModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-[#1F3A8A]" />
                <h3 className="text-sm font-bold text-slate-900">Capture {label} Photo</h3>
              </div>
              <button
                type="button"
                onClick={closeCameraModal}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">
              {cameraError ? (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 space-y-3">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span className="font-medium">{cameraError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      closeCameraModal();
                      fileInputRef.current?.click();
                    }}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#1F3A8A] text-white font-bold text-xs hover:bg-blue-900 cursor-pointer"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Image Instead</span>
                  </button>
                </div>
              ) : (
                <>
                  <div className="relative bg-slate-950 rounded-xl overflow-hidden aspect-4/3 flex items-center justify-center">
                    <video
                      ref={videoRef}
                      playsInline
                      muted
                      className="w-full h-full object-contain"
                    />
                    {!cameraReady && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-white/80 text-xs gap-2">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span>Starting camera...</span>
                      </div>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 text-center">
                    Hold steady and ensure all numbers on the {label.toLowerCase()} are clear and free of glare.
                  </p>
                </>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-slate-100 bg-slate-50">
              <button
                type="button"
                onClick={closeCameraModal}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                Cancel
              </button>
              {!cameraError && (
                <button
                  type="button"
                  onClick={handleCaptureFrame}
                  disabled={!cameraReady}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#1F3A8A] hover:bg-blue-900 disabled:opacity-50 text-white text-xs font-bold cursor-pointer shadow-xs"
                >
                  <Aperture className="w-3.5 h-3.5" />
                  <span>Capture Photo</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
