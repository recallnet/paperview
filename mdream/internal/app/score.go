package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newScoreCommand() *cobra.Command {
	scoreCmd := &cobra.Command{
		Use:   "score",
		Short: "Inspect stored scores and score-related evidence",
	}

	var paperID string
	var runID string
	paperCmd := &cobra.Command{
		Use:   "paper",
		Short: "Get diamond score drilldown for one paper",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			activeRunID := runID
			if activeRunID == "" {
				activeRunID, err = core.LatestRunID(runtime.SourceDB, "diamond_scores")
				if err != nil {
					return err
				}
			}
			scoreRows, err := core.QueryRows(runtime.SourceDB, `SELECT * FROM diamond_scores WHERE run_id = ? AND paper_id = ?`, activeRunID, paperID)
			if err != nil {
				return err
			}
			echoRows, err := core.QueryRows(runtime.SourceDB, `SELECT run_id, shortlist_id, holdout_paper_id, echo_score, echo_rank, source_paper_ids_json FROM holdout_echoes WHERE source_paper_ids_json LIKE ? ORDER BY echo_score DESC LIMIT 10`, "%"+paperID+"%")
			if err != nil {
				return err
			}
			bridgeRows, err := core.QueryRows(runtime.SourceDB, `SELECT source_anchor_id, target_anchor_id, bridge_score, bridge_rank FROM bridge_candidates WHERE paper_id = ? ORDER BY bridge_score DESC LIMIT 10`, paperID)
			if err != nil {
				return err
			}
			compositionRows, err := core.QueryRows(runtime.SourceDB, `SELECT source_anchor_id, target_anchor_id, composition_score, composition_rank FROM composition_candidates WHERE paper_id = ? ORDER BY composition_score DESC LIMIT 10`, paperID)
			if err != nil {
				return err
			}
			payload := map[string]any{
				"run_id":             activeRunID,
				"score_items":        scoreRows,
				"holdout_echo_items": echoRows,
				"bridge_items":       bridgeRows,
				"composition_items":  compositionRows,
			}
			totalItems := len(scoreRows) + len(echoRows) + len(bridgeRows) + len(compositionRows)
			summary := fmt.Sprintf("score_paper: paper_id=%s score_rows=%d holdout_echoes=%d bridge_hits=%d composition_hits=%d", paperID, len(scoreRows), len(echoRows), len(bridgeRows), len(compositionRows))
			return emitAndStore(cmd, "score_paper", summary, payload, totalItems, map[string]any{"paper_id": paperID, "run_id": activeRunID})
		},
	}
	paperCmd.Flags().StringVar(&paperID, "paper-id", "", "Paper ID")
	paperCmd.Flags().StringVar(&runID, "run-id", "", "Optional diamond score run ID")
	_ = paperCmd.MarkFlagRequired("paper-id")

	scoreCmd.AddCommand(paperCmd)
	return scoreCmd
}
