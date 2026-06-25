import { useRef, useState } from "react";
import { Upload, File, X } from "lucide-react";

interface Props {
  id: string;
  file: File | null;
  onFile: (f: File | null) => void;
  accept?: string;
}

export default function FileUploadZone({ id, file, onFile, accept = ".csv" }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) onFile(f);
  };

  if (file) {
    return (
      <div className="flex items-center justify-between px-3 py-2.5 border border-zinc-200 rounded-lg bg-zinc-50">
        <div className="flex items-center gap-2 min-w-0">
          <File size={14} className="text-zinc-500 shrink-0" />
          <span className="text-sm text-zinc-700 truncate">{file.name}</span>
          <span className="text-xs text-zinc-400 shrink-0">({(file.size / 1024).toFixed(1)} KB)</span>
        </div>
        <button
          type="button"
          onClick={() => { onFile(null); if (inputRef.current) inputRef.current.value = ""; }}
          className="ml-2 text-zinc-400 hover:text-zinc-700 transition-colors shrink-0"
          aria-label="Remove file"
        >
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div
      id={id}
      className={`border-2 border-dashed rounded-lg px-4 py-6 text-center cursor-pointer transition-colors ${
        dragging ? "border-zinc-500 bg-zinc-50" : "border-zinc-200 hover:border-zinc-400 hover:bg-zinc-50"
      }`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <Upload size={18} className="text-zinc-400 mx-auto mb-2" />
      <p className="text-sm text-zinc-500">
        Drag & drop or <span className="text-zinc-900 font-medium">browse</span>
      </p>
      <p className="text-xs text-zinc-400 mt-1">{accept.toUpperCase()} files only</p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
}
