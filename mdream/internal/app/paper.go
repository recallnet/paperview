package app

import (
	"database/sql"
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newPaperCommand() *cobra.Command {
	paperCmd := &cobra.Command{
		Use:   "paper",
		Short: "Inspect papers, sections, and neighbors",
	}

	var paperID string
	getCmd := &cobra.Command{
		Use:   "get",
		Short: "Get one paper",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.SourceDB, `SELECT paper_id, title, abstract, authors_json, categories_json, primary_category, published_at, updated_at, literature_family, evaluation_split FROM papers WHERE paper_id = ?`, paperID)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("paper", items)
			return emitAndStore(cmd, "paper_get", summary, map[string]any{"items": items}, len(items), map[string]any{"paper_id": paperID})
		},
	}
	getCmd.Flags().StringVar(&paperID, "paper-id", "", "Paper ID")
	_ = getCmd.MarkFlagRequired("paper-id")

	var sectionsPaperID string
	var sectionLabel string
	var sectionLimit int
	sectionsCmd := &cobra.Command{
		Use:   "sections",
		Short: "List extracted sections for a paper",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			query := `SELECT section_id, paper_id, section_label, section_order, substr(replace(replace(content_text, char(10), ' '), char(13), ' '), 1, 400) AS snippet FROM paper_sections WHERE paper_id = ?`
			args := []any{sectionsPaperID}
			if sectionLabel != "" {
				query += ` AND section_label = ?`
				args = append(args, sectionLabel)
			}
			query += ` ORDER BY section_order, section_id LIMIT ?`
			args = append(args, sectionLimit)
			items, err := core.QueryRows(runtime.SourceDB, query, args...)
			if err != nil {
				return err
			}
			if len(items) == 0 {
				items, err = core.QueryRows(runtime.SourceDB, `SELECT view_id AS section_id, paper_id, view_type AS section_label, 0 AS section_order, substr(replace(replace(text, char(10), ' '), char(13), ' '), 1, 400) AS snippet FROM text_views WHERE paper_id = ? AND view_type = 'section_or_abs'`, sectionsPaperID)
				if err != nil {
					return err
				}
			}
			summary := core.SummarizeList("paper_sections", items)
			return emitAndStore(cmd, "paper_sections", summary, map[string]any{"items": items}, len(items), map[string]any{"paper_id": sectionsPaperID, "section_label": sectionLabel, "limit": sectionLimit})
		},
	}
	sectionsCmd.Flags().StringVar(&sectionsPaperID, "paper-id", "", "Paper ID")
	sectionsCmd.Flags().StringVar(&sectionLabel, "section-label", "", "Optional exact section label")
	sectionsCmd.Flags().IntVar(&sectionLimit, "limit", 25, "Maximum stored sections")
	_ = sectionsCmd.MarkFlagRequired("paper-id")

	var neighborsPaperID string
	var viewType string
	var runID string
	var neighborLimit int
	neighborsCmd := &cobra.Command{
		Use:   "neighbors",
		Short: "Show nearest paper neighbors from the KNN graph",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			activeRunID := runID
			if activeRunID == "" {
				activeRunID, err = latestNonEmpty(runtime.SourceDB, "knn_edges")
				if err != nil {
					return err
				}
			}
			items, err := core.QueryRows(runtime.SourceDB, `
SELECT
  tv.paper_id AS source_paper_id,
  ke.target_view_id,
  target.paper_id AS target_paper_id,
  p.title AS target_title,
  ke.rank,
  ke.distance
FROM text_views tv
JOIN knn_edges ke
  ON ke.source_view_id = tv.view_id
JOIN text_views target
  ON target.view_id = ke.target_view_id
JOIN papers p
  ON p.paper_id = target.paper_id
WHERE ke.run_id = ?
  AND tv.paper_id = ?
  AND tv.view_type = ?
ORDER BY ke.rank
LIMIT ?`, activeRunID, neighborsPaperID, viewType, neighborLimit)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("paper_neighbors", items)
			return emitAndStore(cmd, "paper_neighbors", summary, map[string]any{"items": items, "run_id": activeRunID}, len(items), map[string]any{"paper_id": neighborsPaperID, "view_type": viewType, "run_id": activeRunID, "limit": neighborLimit})
		},
	}
	neighborsCmd.Flags().StringVar(&neighborsPaperID, "paper-id", "", "Paper ID")
	neighborsCmd.Flags().StringVar(&viewType, "view-type", "title_abs", "Source text view type")
	neighborsCmd.Flags().StringVar(&runID, "run-id", "", "Optional KNN run ID")
	neighborsCmd.Flags().IntVar(&neighborLimit, "limit", 20, "Maximum stored neighbors")
	_ = neighborsCmd.MarkFlagRequired("paper-id")

	paperCmd.AddCommand(getCmd, sectionsCmd, neighborsCmd)
	return paperCmd
}

func latestNonEmpty(db *sql.DB, table string) (string, error) {
	return core.LatestRunID(db, table)
}

func requireOne(items []map[string]any, label string) error {
	if len(items) == 1 {
		return nil
	}
	if len(items) == 0 {
		return sql.ErrNoRows
	}
	return fmt.Errorf("%s returned %d rows", label, len(items))
}
