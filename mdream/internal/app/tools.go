package app

import (
	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newToolsCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "tools",
		Short: "List the mdream CLI tools available to a research agent",
		RunE: func(cmd *cobra.Command, _ []string) error {
			items := []map[string]any{
				{"tool": "init", "purpose": "initialize or inspect the local mdream store"},
				{"tool": "session create|get|list", "purpose": "create and inspect research sessions"},
				{"tool": "note add|list", "purpose": "store observations linked to sessions, papers, or prior results"},
				{"tool": "hypothesis add|list", "purpose": "store candidate hypotheses for a session"},
				{"tool": "search papers|sections", "purpose": "lexically search papers and extracted sections"},
				{"tool": "discover round", "purpose": "run one prompt-driven discovery pass and store ranked cross-lane leads for follow-up"},
				{"tool": "paper get|sections|neighbors", "purpose": "drill into one paper and its local retrieval neighborhood"},
				{"tool": "surface list|get", "purpose": "inspect canonical publication and review surfaces"},
				{"tool": "score paper", "purpose": "inspect stored diamond scores, echoes, and operator evidence for a paper"},
				{"tool": "result get", "purpose": "reload any stored query result with paging or full output"},
			}
			summary := core.SummarizeList("tools", items)
			return emitAndStore(cmd, "tools", summary, map[string]any{"items": items}, len(items), map[string]any{})
		},
	}
}
