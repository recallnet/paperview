package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

type surfaceDef struct {
	Table     string
	OrderBy   string
	IDColumn  string
	RunScoped bool
	RunColumn string
}

var surfaceMap = map[string]surfaceDef{
	"diamond-board":  {Table: "diamond_board_entries", OrderBy: "board_rank", IDColumn: "publication_item_id", RunScoped: true, RunColumn: "run_id"},
	"unrealized":     {Table: "unrealized_idea_index", OrderBy: "index_rank", IDColumn: "shortlist_id", RunScoped: true, RunColumn: "run_id"},
	"stranded":       {Table: "stranded_result_ledger", OrderBy: "ledger_rank", IDColumn: "shortlist_id", RunScoped: true, RunColumn: "run_id"},
	"transition":     {Table: "transition_state_ledger", OrderBy: "ledger_rank", IDColumn: "pattern_id", RunScoped: true, RunColumn: "run_id"},
	"early-market":   {Table: "early_market_failure_modes_ledger", OrderBy: "ledger_rank", IDColumn: "batch_item_id", RunScoped: true, RunColumn: "run_id"},
	"review-packets": {Table: "review_packets", OrderBy: "packet_kind, item_ref", IDColumn: "item_ref", RunScoped: true, RunColumn: "run_id"},
}

func newSurfaceCommand() *cobra.Command {
	surfaceCmd := &cobra.Command{
		Use:   "surface",
		Short: "List and drill publication and review surfaces",
	}

	var surface string
	var runID string
	var limit int
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List one named surface",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			def, ok := surfaceMap[surface]
			if !ok {
				return fmt.Errorf("unknown surface %q", surface)
			}
			activeRunID := runID
			if def.RunScoped && activeRunID == "" {
				activeRunID, err = core.LatestRunID(runtime.SourceDB, def.Table)
				if err != nil {
					return err
				}
			}
			query := fmt.Sprintf("SELECT * FROM %s", def.Table)
			args := []any{}
			if def.RunScoped {
				query += fmt.Sprintf(" WHERE %s = ?", def.RunColumn)
				args = append(args, activeRunID)
			}
			query += fmt.Sprintf(" ORDER BY %s LIMIT ?", def.OrderBy)
			args = append(args, limit)
			items, err := core.QueryRows(runtime.SourceDB, query, args...)
			if err != nil {
				return err
			}
			summary := core.SummarizeList(surface, items)
			return emitAndStore(cmd, "surface_list", summary, map[string]any{"surface": surface, "run_id": activeRunID, "items": items}, len(items), map[string]any{"surface": surface, "run_id": activeRunID, "limit": limit})
		},
	}
	listCmd.Flags().StringVar(&surface, "surface", "", "Named surface")
	listCmd.Flags().StringVar(&runID, "run-id", "", "Optional explicit run ID")
	listCmd.Flags().IntVar(&limit, "limit", 25, "Maximum stored rows")
	_ = listCmd.MarkFlagRequired("surface")

	var getSurface string
	var getRunID string
	var itemID string
	getCmd := &cobra.Command{
		Use:   "get",
		Short: "Get one row from a named surface",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			def, ok := surfaceMap[getSurface]
			if !ok {
				return fmt.Errorf("unknown surface %q", getSurface)
			}
			activeRunID := getRunID
			if def.RunScoped && activeRunID == "" {
				activeRunID, err = core.LatestRunID(runtime.SourceDB, def.Table)
				if err != nil {
					return err
				}
			}
			query := fmt.Sprintf("SELECT * FROM %s WHERE %s = ?", def.Table, def.IDColumn)
			args := []any{itemID}
			if def.RunScoped {
				query += fmt.Sprintf(" AND %s = ?", def.RunColumn)
				args = append(args, activeRunID)
			}
			items, err := core.QueryRows(runtime.SourceDB, query, args...)
			if err != nil {
				return err
			}
			summary := core.SummarizeList(getSurface, items)
			return emitAndStore(cmd, "surface_get", summary, map[string]any{"surface": getSurface, "run_id": activeRunID, "items": items}, len(items), map[string]any{"surface": getSurface, "run_id": activeRunID, "item_id": itemID})
		},
	}
	getCmd.Flags().StringVar(&getSurface, "surface", "", "Named surface")
	getCmd.Flags().StringVar(&getRunID, "run-id", "", "Optional explicit run ID")
	getCmd.Flags().StringVar(&itemID, "item-id", "", "Surface row identifier")
	_ = getCmd.MarkFlagRequired("surface")
	_ = getCmd.MarkFlagRequired("item-id")

	surfaceCmd.AddCommand(listCmd, getCmd)
	return surfaceCmd
}
