import { TraceList } from "@/components/TraceList";

export default function SladyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Ślady zapytań</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Oś czasu pod-wywołań każdego zapytania (retrieval, generacja, narzędzia) — lekka
          obserwowalność bez zewnętrznej infrastruktury.
        </p>
      </div>
      <TraceList />
    </div>
  );
}
