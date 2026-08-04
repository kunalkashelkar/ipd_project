import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { FiUploadCloud, FiFile, FiCheckCircle, FiLoader } from 'react-icons/fi';
import clsx from 'clsx';
import { uploadFile, queueParse } from '../services/api';

type Stage = 'idle' | 'uploading' | 'parsing' | 'done' | 'error';

export default function Upload() {
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>('idle');
  const [dragging, setDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState('');
  const [error, setError] = useState('');

  const handleFile = useCallback(async (file: File) => {
    setSelectedFile(file);
    setStage('uploading');
    setError('');

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(p => Math.min(p + 15, 90));
    }, 200);

    try {
      const uploaded = await uploadFile(file);
      clearInterval(interval);
      setUploadProgress(100);
      toast.success(`Uploaded: ${uploaded.original_filename}`);

      setStage('parsing');
      const job = await queueParse(uploaded.id, uploaded.project_id);
      setJobId(job.job_id);
      toast.success('Parse job queued!');
      setStage('done');
    } catch (err: unknown) {
      clearInterval(interval);
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed.';
      setError(msg);
      setStage('error');
      toast.error(msg);
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="max-w-2xl mx-auto py-8 animate-slide-up">
      <h1 className="text-3xl font-bold text-surface-900 mb-2">Upload Source Code</h1>
      <p className="text-surface-500 mb-8">Upload a C, C++, or ZIP file to begin analysis.</p>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={clsx(
          'relative flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-12 transition-all duration-300 cursor-pointer',
          dragging ? 'border-primary-500 bg-primary-50 scale-[1.01]' : 'border-surface-300 bg-white hover:border-primary-400 hover:bg-primary-50/40',
        )}
      >
        <input
          type="file"
          accept=".c,.cpp,.h,.hpp,.zip"
          className="absolute inset-0 opacity-0 cursor-pointer"
          onChange={onInputChange}
          disabled={stage === 'uploading' || stage === 'parsing'}
        />
        <FiUploadCloud className="w-14 h-14 text-primary-400 mb-4" />
        <p className="text-lg font-semibold text-surface-700">Drag & drop or click to browse</p>
        <p className="text-sm text-surface-400 mt-1">Accepts .c · .cpp · .h · .hpp · .zip (max 50 MB)</p>
      </div>

      {/* Selected file */}
      {selectedFile && (
        <div className="mt-6 flex items-center gap-3 p-4 bg-surface-50 rounded-xl border border-surface-200 animate-fade-in">
          <FiFile className="text-primary-500 w-5 h-5 shrink-0" />
          <span className="text-surface-700 font-medium truncate">{selectedFile.name}</span>
          <span className="ml-auto text-surface-400 text-sm">{(selectedFile.size / 1024).toFixed(1)} KB</span>
        </div>
      )}

      {/* Progress bar */}
      {(stage === 'uploading') && (
        <div className="mt-4 animate-fade-in">
          <div className="flex justify-between text-sm text-surface-500 mb-1">
            <span>Uploading…</span><span>{uploadProgress}%</span>
          </div>
          <div className="w-full bg-surface-200 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Parsing spinner */}
      {stage === 'parsing' && (
        <div className="mt-6 flex items-center gap-3 text-primary-600 animate-fade-in">
          <FiLoader className="w-5 h-5 animate-spin" />
          <span className="font-medium">Queuing parse job…</span>
        </div>
      )}

      {/* Done */}
      {stage === 'done' && (
        <div className="mt-6 animate-fade-in">
          <div className="flex items-center gap-3 text-accent-emerald mb-4">
            <FiCheckCircle className="w-6 h-6" />
            <span className="font-semibold text-lg">Parse job queued successfully</span>
          </div>
          <button
            onClick={() => navigate(`/analysis/${jobId}`)}
            className="btn-primary mt-2"
          >
            View Analysis →
          </button>
        </div>
      )}

      {/* Error */}
      {stage === 'error' && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 animate-fade-in">
          <p className="font-semibold">Upload failed</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}
    </div>
  );
}
