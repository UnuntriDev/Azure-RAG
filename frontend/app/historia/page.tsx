import { HistoryList } from "@/components/HistoryList";

export default function HistoriaPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight text-foreground">Historia rozmów</h1>
      <HistoryList />
    </div>
  );
}
