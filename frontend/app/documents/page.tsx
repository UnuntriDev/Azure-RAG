import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { DocumentList } from "@/components/DocumentList";

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Dokumenty</h1>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="size-4" /> Wgraj dokument
        </Link>
      </div>

      <DocumentList />
    </div>
  );
}
