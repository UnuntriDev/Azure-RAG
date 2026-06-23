import { Suspense } from "react";

import { ChatView } from "@/components/ChatView";

export default function Home() {
  // useSearchParams() requires a Suspense boundary when statically prerendered.
  return (
    <Suspense>
      <ChatView />
    </Suspense>
  );
}
