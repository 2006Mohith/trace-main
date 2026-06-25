import { AlertTriangle, Info, CheckCircle, type LucideProps } from "lucide-react";

type Variant = "error" | "warning" | "success" | "info";

interface Props {
  message: string;
  variant?: Variant;
  onDismiss?: () => void;
}

const CONFIG: Record<Variant, { bg: string; border: string; text: string; Icon: React.FC<LucideProps> }> = {
  error:   { bg: "bg-red-50",   border: "border-red-200",   text: "text-red-700",   Icon: AlertTriangle },
  warning: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", Icon: AlertTriangle },
  success: { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", Icon: CheckCircle },
  info:    { bg: "bg-zinc-50",  border: "border-zinc-200",  text: "text-zinc-700",  Icon: Info },
};

export default function AlertBanner({ message, variant = "info", onDismiss }: Props) {
  const { bg, border, text, Icon } = CONFIG[variant];
  return (
    <div className={`flex items-start gap-2 p-3 rounded-lg border text-sm ${bg} ${border} ${text}`}>
      <Icon size={15} className="mt-0.5 shrink-0" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 hover:opacity-70 transition-opacity text-xs ml-2"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}
