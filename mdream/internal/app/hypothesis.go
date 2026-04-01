package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newHypothesisCommand() *cobra.Command {
	hypCmd := &cobra.Command{
		Use:   "hypothesis",
		Short: "Store and inspect working hypotheses",
	}

	var sessionID string
	var title string
	var hypothesisText string
	var targetMarket string
	addCmd := &cobra.Command{
		Use:   "add",
		Short: "Add a working hypothesis to a session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			hypothesisID, err := core.SaveHypothesis(runtime.StoreDB, sessionID, title, hypothesisText, targetMarket)
			if err != nil {
				return err
			}
			payload := map[string]any{
				"hypothesis_id": hypothesisID,
				"session_id":    sessionID,
				"title":         title,
				"hypothesis":    hypothesisText,
				"target_market": targetMarket,
			}
			summary := fmt.Sprintf("hypothesis saved: hypothesis_id=%s session_id=%s", hypothesisID, sessionID)
			return emitAndStore(cmd, "hypothesis_add", summary, payload, 1, payload)
		},
	}
	addCmd.Flags().StringVar(&sessionID, "session-id", "", "Session ID")
	addCmd.Flags().StringVar(&title, "title", "", "Short hypothesis title")
	addCmd.Flags().StringVar(&hypothesisText, "text", "", "Hypothesis text")
	addCmd.Flags().StringVar(&targetMarket, "target-market", "", "Target market or venue family")
	_ = addCmd.MarkFlagRequired("session-id")
	_ = addCmd.MarkFlagRequired("title")
	_ = addCmd.MarkFlagRequired("text")

	var listSessionID string
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List stored hypotheses for a session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.StoreDB, `SELECT hypothesis_id, title, target_market, status, created_at FROM hypotheses WHERE session_id = ? ORDER BY created_at DESC LIMIT 100`, listSessionID)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("hypotheses", items)
			return emitAndStore(cmd, "hypothesis_list", summary, map[string]any{"items": items}, len(items), map[string]any{"session_id": listSessionID})
		},
	}
	listCmd.Flags().StringVar(&listSessionID, "session-id", "", "Session ID")
	_ = listCmd.MarkFlagRequired("session-id")

	hypCmd.AddCommand(addCmd, listCmd)
	return hypCmd
}
