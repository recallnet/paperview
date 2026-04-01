package app

import (
	"fmt"
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
			tokens := core.ExpandResearchTokens(q)
			if len(tokens) == 0 {
				tokens = []string{strings.ToLower(q)}
			}
			scoreExpr, whereExpr, args := tokenizedPaperSearch(tokens)
			args = append(args, limit)
			items, err := core.QueryRows(runtime.SourceDB, fmt.Sprintf(`
SELECT
  paper_id,
  title,
  primary_category,
  published_at,
  (%s) AS lexical_score,
  substr(replace(replace(COALESCE(abstract, ''), char(10), ' '), char(13), ' '), 1, 220) AS abstract_snippet
FROM papers
WHERE (%s)
ORDER BY lexical_score DESC, COALESCE(published_at, '') DESC, paper_id
LIMIT ?`, scoreExpr, whereExpr), args...)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("paper_search", items)
			return emitAndStore(cmd, "paper_search", summary, map[string]any{"items": items, "query": q, "tokens": tokens}, len(items), map[string]any{"query": q, "tokens": tokens, "limit": limit})
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
			tokens := core.ExpandResearchTokens(q)
			if len(tokens) == 0 {
				tokens = []string{strings.ToLower(q)}
			}
			scoreExpr, whereExpr, args := tokenizedSectionSearch(tokens)
			args = append(args, sectionLimit)
			items, err := core.QueryRows(runtime.SourceDB, fmt.Sprintf(`
SELECT
  ps.section_id,
  ps.paper_id,
  p.title,
  ps.section_label,
  ps.section_order,
  (%s) AS lexical_score,
  substr(replace(replace(ps.content_text, char(10), ' '), char(13), ' '), 1, 220) AS snippet
FROM paper_sections ps
JOIN papers p ON p.paper_id = ps.paper_id
WHERE (%s)
  AND lower(COALESCE(ps.section_label, '')) NOT IN ('front_matter', 'references')
ORDER BY lexical_score DESC, COALESCE(p.published_at, '') DESC, ps.paper_id, ps.section_order
LIMIT ?`, scoreExpr, whereExpr), args...)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("section_search", items)
			return emitAndStore(cmd, "section_search", summary, map[string]any{"items": items, "query": q, "tokens": tokens}, len(items), map[string]any{"query": q, "tokens": tokens, "limit": sectionLimit})
		},
	}
	sectionsCmd.Flags().StringVar(&sectionQuery, "query", "", "Section search query")
	sectionsCmd.Flags().IntVar(&sectionLimit, "limit", 25, "Maximum stored matches")
	_ = sectionsCmd.MarkFlagRequired("query")

	searchCmd.AddCommand(papersCmd, sectionsCmd)
	return searchCmd
}

func tokenizedPaperSearch(tokens []string) (string, string, []any) {
	scoreParts := make([]string, 0, len(tokens)*3)
	whereParts := make([]string, 0, len(tokens))
	scoreArgs := make([]any, 0, len(tokens)*3)
	whereArgs := make([]any, 0, len(tokens))
	for _, token := range tokens {
		like := "%" + token + "%"
		scoreParts = append(scoreParts, "CASE WHEN lower(COALESCE(title, '')) LIKE ? THEN 5 ELSE 0 END")
		scoreParts = append(scoreParts, "CASE WHEN lower(COALESCE(abstract, '')) LIKE ? THEN 3 ELSE 0 END")
		scoreParts = append(scoreParts, "CASE WHEN lower(COALESCE(categories_json, '')) LIKE ? THEN 1 ELSE 0 END")
		scoreArgs = append(scoreArgs, like, like, like)
		whereParts = append(whereParts, "lower(COALESCE(title, '') || ' ' || COALESCE(abstract, '') || ' ' || COALESCE(categories_json, '')) LIKE ?")
		whereArgs = append(whereArgs, like)
	}
	args := append(scoreArgs, whereArgs...)
	return strings.Join(scoreParts, " + "), strings.Join(whereParts, " OR "), args
}

func tokenizedSectionSearch(tokens []string) (string, string, []any) {
	scoreParts := make([]string, 0, len(tokens)*2)
	whereParts := make([]string, 0, len(tokens))
	scoreArgs := make([]any, 0, len(tokens)*2)
	whereArgs := make([]any, 0, len(tokens))
	for _, token := range tokens {
		like := "%" + token + "%"
		scoreParts = append(scoreParts, "CASE WHEN lower(ps.section_label) LIKE ? THEN 2 ELSE 0 END")
		scoreParts = append(scoreParts, "CASE WHEN lower(ps.content_text) LIKE ? THEN 4 ELSE 0 END")
		scoreArgs = append(scoreArgs, like, like)
		whereParts = append(whereParts, "lower(ps.section_label || ' ' || ps.content_text) LIKE ?")
		whereArgs = append(whereArgs, like)
	}
	args := append(scoreArgs, whereArgs...)
	return strings.Join(scoreParts, " + "), strings.Join(whereParts, " OR "), args
}
