import { Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";

/** Suspense fallback with the interview layout, to avoid a blank screen and layout shift. */
export function InterviewSkeleton({ embedded = false }: { embedded?: boolean }) {
  return (
    <div
      className={cn(
        "mx-auto grid max-w-7xl gap-6 px-3 sm:px-5 lg:grid-cols-[minmax(0,1fr)_380px]",
        embedded ? "h-dvh" : "h-[calc(100dvh-4rem)]",
      )}
    >
      <div className="flex min-h-0 flex-col">
        <div className="flex items-center gap-3 py-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <div className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-2.5 w-14" />
          </div>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center gap-6">
          <Skeleton className="h-40 w-40 rounded-full" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="mx-auto mb-4 h-14 w-full max-w-3xl rounded-2xl" />
      </div>
      <div className="hidden py-4 lg:block">
        <Skeleton className="h-full rounded-2xl" />
      </div>
    </div>
  );
}
