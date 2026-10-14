"use client";

import { Activity, FileText } from "lucide-react";
import type { Dictionary } from "@/app/[lang]/dictionaries";
import type { UiMessage } from "@/lib/use-interview";
import { Tabs } from "@/components/ui/tabs";
import { SourcesList } from "./sources-list";
import { TraceTimeline } from "./trace-timeline";

export type InspectorTab = "sources" | "trace";

interface Props {
  message: UiMessage | null;
  tab: InspectorTab;
  onTab: (tab: InspectorTab) => void;
  activeCite: number | null;
  dict: Dictionary["interview"];
}

/** "Glass box": the sources and the agent trace behind the selected answer. */
export function Inspector({ message, tab, onTab, activeCite, dict }: Props) {
  return (
    <Tabs
      className="h-full"
      label={dict.panel.label}
      value={tab}
      onChange={onTab}
      items={[
        {
          id: "sources",
          label: dict.panel.sources,
          icon: <FileText className="h-4 w-4" />,
          count: message?.citations.length,
        },
        { id: "trace", label: dict.panel.trace, icon: <Activity className="h-4 w-4" /> },
      ]}
    >
      {tab === "sources" ? (
        <SourcesList citations={message?.citations ?? []} activeCite={activeCite} empty={dict.panel.noSources} />
      ) : (
        <TraceTimeline message={message} dict={dict} />
      )}
    </Tabs>
  );
}
