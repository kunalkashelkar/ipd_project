import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Play, FileCode2, Layers, AlertTriangle, CheckCircle2, Clock, Loader2, Upload as UploadIcon, Trash2, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { projectService } from '../../services/projectService';
import { uploadService } from '../../services/uploadService';
import { scanService } from '../../services/scanService';
import { Project, Upload, Scan } from '../../types';
import toast from 'react-hot-toast';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!id) return;
    async function load() {
      setLoading(true);
      try {
        const [proj, uploadsData, scansData] = await Promise.allSettled([
          projectService.getProject(id!),
          uploadService.listUploads(id!, { page_size: 50 }),
          scanService.listScans({ project_id: id!, page_size: 50 }),
        ]);

        if (proj.status === 'fulfilled') setProject(proj.value);
        if (uploadsData.status === 'fulfilled') setUploads(uploadsData.value.items);
        if (scansData.status === 'fulfilled') setScans(scansData.value.items);
      } catch {
        // Handled by interceptor
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;

    setUploading(true);
    setUploadProgress(0);
    try {
      const upload = await uploadService.uploadFile(id, file, (p) => setUploadProgress(p));
      setUploads((prev) => [upload, ...prev]);
      toast.success(`Uploaded ${file.name} successfully!`);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        <p className="text-lg font-medium">Project not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
            <Badge variant="outline" className="text-muted-foreground">
              {project.is_archived ? 'Archived' : 'Active'}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-3">
            <span className="flex items-center gap-1.5"><FileCode2 className="w-4 h-4" /> {project.language || 'Unknown'}</span>
            <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> Created {new Date(project.created_at).toLocaleDateString()}</span>
            <span className="flex items-center gap-1.5 text-emerald-500"><CheckCircle2 className="w-4 h-4" /> Active</span>
          </div>
          {project.description && (
            <p className="text-sm text-muted-foreground mt-2">{project.description}</p>
          )}
        </div>

        <div className="flex gap-3">
          {uploads.length > 0 && (
            <Link to={`/projects/${project.id}/scan-config`}>
              <Button>
                <Play className="w-4 h-4 mr-2" />
                Run Security Scan
              </Button>
            </Link>
          )}
        </div>
      </div>

      <div className="border-b border-border mt-4">
        <div className="flex gap-6">
          {['overview', 'uploads', 'scans'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium transition-colors capitalize ${activeTab === tab
                  ? 'border-b-2 border-primary text-foreground'
                  : 'text-muted-foreground hover:text-foreground border-transparent'
                }`}
            >
              {tab} {tab === 'uploads' && `(${uploads.length})`} {tab === 'scans' && `(${scans.length})`}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Uploads</p>
                  <UploadIcon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold">{uploads.length}</div>
              </CardContent>
            </Card>
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Scans</p>
                  <Layers className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold">{scans.length}</div>
              </CardContent>
            </Card>
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Language</p>
                  <FileCode2 className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold text-base mt-1">{project.language || '—'}</div>
              </CardContent>
            </Card>
            <Card className="hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-center justify-between space-y-0 pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Latest Scan</p>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold text-base mt-1">
                  {scans.length > 0
                    ? scans[0].status.charAt(0).toUpperCase() + scans[0].status.slice(1)
                    : 'None'}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Upload area */}
          <Card>
            <CardHeader>
              <CardTitle>Upload Source Code</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-primary/5 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip,.jar,.java,.py,.js,.ts,.c,.cpp,.h,.hpp"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                {uploading ? (
                  <div className="space-y-3">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
                    <p className="text-sm text-muted-foreground">Uploading... {uploadProgress}%</p>
                    <div className="w-full max-w-xs mx-auto bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    <UploadIcon className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
                    <p className="font-medium text-foreground">Click to upload or drag and drop</p>
                    <p className="text-xs text-muted-foreground mt-1">.zip, .jar, .java, .py, .c, .cpp, .h, .js, .ts</p>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'uploads' && (
        <div className="space-y-3">
          {uploads.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <UploadIcon className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No uploads yet. Upload source code from the Overview tab.</p>
            </div>
          ) : (
            uploads.map((upload) => (
              <Card key={upload.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-sm">{upload.original_filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {(upload.file_size / 1024).toFixed(1)} KB • {upload.file_extension} • {new Date(upload.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">{upload.status}</Badge>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'scans' && (
        <div className="space-y-3">
          {scans.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Layers className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No scans yet. Upload files and start a scan.</p>
            </div>
          ) : (
            scans.map((scan) => (
              <Card key={scan.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">Scan {scan.id.slice(0, 8)}...</p>
                    <p className="text-xs text-muted-foreground">
                      {scan.current_stage || scan.status} • {scan.progress}% • {new Date(scan.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        scan.status === 'completed' ? 'safe' :
                        scan.status === 'failed' ? 'destructive' :
                        'warning'
                      }
                    >
                      {scan.status}
                    </Badge>
                    {scan.status === 'completed' && (
                      <Link to={`/projects/${project.id}/results?scan_id=${scan.id}`}>
                        <Button variant="outline" size="sm">View Results</Button>
                      </Link>
                    )}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
