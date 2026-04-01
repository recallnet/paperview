package app

import (
	"strings"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newSearchCommand() *cobra.Command {
	searchCmd := &cobra.Command{
		Use:   "search",
		Short: "Search papers and sections",
	}

	var query string
	var limit int
	papersCmd := &cobra.Command{
		Use:   "papers",
		Short: "Lexically search papers",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			q := strings.TrimSpace(query)
			like := core.LowerLikeQuery(q)
			items, err := core.QueryRows(runtime.SourceDB, `
SELECT
  paper_id,
  title,
  primary_category,
  published_at,
  (
    CASE WHEN lower(COALESCE(title, '')) LIKE ? THEN 5 ELSE 0 END +
    CASE WHEN lower(COALESCE(abstract, '')) LIKE ? THEN 3 ELSE 0 END +
    CASE WHEN lower(COALESCE(categories_json, '')) LIKE ? THEN 1 ELSE 0 END
  ) AS lexical_score,
  substr(replace(replace(COALESCE(abstract, ''), char(10), ' '), char(13), ' '), 1, 220) AS abstract_snippet
FROM papers
WHERE lower(COALESCE(title, '') || ' ' || COALESCE(abstract, '') || ' ' || COALESCE(categories_json, '')) LIKE ?
ORDER BY lexical_score DESC, COALESCE(published_at, '') DESC, paper_id
LIMIT ?`, like, like, like, like, limit)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("paper_search", items)
			return emitAndStore(cmd, "paper_search", summary, map[string]any{"items": items, "query": q}, len(items), map[string]any{"query": q, "limit": limit})
		},
	}
	papersCmd.Flags().StringVar(&query, "query", "", "Search query")
	papersCmd.Flags().IntVar(&limit, "limit", 25, "Maximum stored matches")
	_ = papersCmd.MarkFlagRequired("query")

	var sectionQuery string
	var sectionLimit int
	sectionsCmd := &cobra.Command{
		Use:   "sections",
		Short: "Lexically search extracted sections",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			q := strings.TrimSpace(sectionQuery)
			like := core.LowerLikeQuery(q)
			items, err := core.QueryRows(runtime.SourceDB, `
SELECT
  ps.section_id,
  ps.paper_id,
  p.title,
  ps.section_label,
  ps.section_order,
  substr(replace(replace(ps.content_text, char(10), ' '), char(13), ' '), 1, 220) AS snippet
FROM paper_sections ps
JOIN papers p ON p.paper_id = ps.paper_id
WHERE lower(ps.content_text) LIKE ?
ORDER BY COALESCE(p.published_at, '') DESC, ps.paper_id, ps.section_order
LIMIT ?`, like, sectionLimit)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("section_search", items)
			return emitAndStore(cmd, "section_search", summary, map[string]any{"items": items, "query": q}, len(items), map[string]any{"query": q, "limit": sectionLimit})
		},
	}
	sectionsCmd.Flags().StringVar(&sectionQuery, "query", "", "Section search query")
	sectionsCmd.Flags().IntVar(&sectionLimit, "limit", 25, "Maximum stored matches")
	_ = sectionsCmd.MarkFlagRequired("query")

	searchCmd.AddCommand(papersCmd, sectionsCmd)
	return searchCmd
}
