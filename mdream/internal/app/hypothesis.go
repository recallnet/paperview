package app

import (
	"fmt"
	"math"

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
			items, err := core.QueryRows(runtime.StoreDB, `
WITH latest_scores AS (
  SELECT *
  FROM (
    SELECT
      hs.*,
      ROW_NUMBER() OVER (PARTITION BY hs.hypothesis_id ORDER BY hs.created_at DESC, hs.score_id DESC) AS rn
    FROM hypothesis_scores hs
  )
  WHERE rn = 1
)
SELECT
  h.hypothesis_id,
  h.title,
  h.target_market,
  h.status,
  ls.objective_score,
  ls.surprise_score,
  ls.result_id,
  h.created_at
FROM hypotheses h
LEFT JOIN latest_scores ls ON ls.hypothesis_id = h.hypothesis_id
WHERE h.session_id = ?
ORDER BY COALESCE(ls.objective_score, -999) DESC, h.created_at DESC
LIMIT 100`, listSessionID)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("hypotheses", items)
			return emitAndStore(cmd, "hypothesis_list", summary, map[string]any{"items": items}, len(items), map[string]any{"session_id": listSessionID})
		},
	}
	listCmd.Flags().StringVar(&listSessionID, "session-id", "", "Session ID")
	_ = listCmd.MarkFlagRequired("session-id")

	var scoreHypothesisID string
	var leadID string
	var paperID string
	var resultID string
	var priorNovelty float64
	var posteriorNovelty float64
	var priorPlausibility float64
	var posteriorPlausibility float64
	var thinMarketFit float64
	var executability float64
	var evidenceQuality float64
	var basinRepetitionPenalty float64
	var genericDragPenalty float64
	var notes string
	scoreCmd := &cobra.Command{
		Use:   "score",
		Short: "Score a hypothesis after reading evidence",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			input := core.HypothesisScoreInput{
				HypothesisID:           scoreHypothesisID,
				LeadID:                 leadID,
				PaperID:                paperID,
				ResultID:               resultID,
				PriorNovelty:           clampScore(priorNovelty),
				PosteriorNovelty:       clampScore(posteriorNovelty),
				PriorPlausibility:      clampScore(priorPlausibility),
				PosteriorPlausibility:  clampScore(posteriorPlausibility),
				ThinMarketFit:          clampScore(thinMarketFit),
				Executability:          clampScore(executability),
				EvidenceQuality:        clampScore(evidenceQuality),
				BasinRepetitionPenalty: clampScore(basinRepetitionPenalty),
				GenericDragPenalty:     clampScore(genericDragPenalty),
				Notes:                  notes,
			}
			input.SurpriseScore = computeSurpriseScore(input)
			input.ObjectiveScore = computeObjectiveScore(input)
			scoreID, err := core.SaveHypothesisScore(runtime.StoreDB, input)
			if err != nil {
				return err
			}
			payload := map[string]any{
				"score_id":                 scoreID,
				"hypothesis_id":            input.HypothesisID,
				"lead_id":                  input.LeadID,
				"paper_id":                 input.PaperID,
				"result_id":                input.ResultID,
				"prior_novelty":            input.PriorNovelty,
				"posterior_novelty":        input.PosteriorNovelty,
				"prior_plausibility":       input.PriorPlausibility,
				"posterior_plausibility":   input.PosteriorPlausibility,
				"thin_market_fit":          input.ThinMarketFit,
				"executability":            input.Executability,
				"evidence_quality":         input.EvidenceQuality,
				"basin_repetition_penalty": input.BasinRepetitionPenalty,
				"generic_drag_penalty":     input.GenericDragPenalty,
				"surprise_score":           input.SurpriseScore,
				"objective_score":          input.ObjectiveScore,
				"notes":                    input.Notes,
			}
			summary := fmt.Sprintf(
				"hypothesis scored: hypothesis_id=%s objective_score=%.2f surprise_score=%.2f",
				input.HypothesisID,
				input.ObjectiveScore,
				input.SurpriseScore,
			)
			return emitAndStore(cmd, "hypothesis_score", summary, payload, 1, payload)
		},
	}
	scoreCmd.Flags().StringVar(&scoreHypothesisID, "hypothesis-id", "", "Hypothesis ID")
	scoreCmd.Flags().StringVar(&leadID, "lead-id", "", "Lead ID from discover round")
	scoreCmd.Flags().StringVar(&paperID, "paper-id", "", "Paper ID if the score is tied to a paper lead")
	scoreCmd.Flags().StringVar(&resultID, "result-id", "", "Stored result ID for the discovery or drilldown step")
	scoreCmd.Flags().Float64Var(&priorNovelty, "prior-novelty", 0, "Prior novelty impression on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&posteriorNovelty, "posterior-novelty", 0, "Posterior novelty impression on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&priorPlausibility, "prior-plausibility", 0, "Prior plausibility impression on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&posteriorPlausibility, "posterior-plausibility", 0, "Posterior plausibility impression on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&thinMarketFit, "thin-market-fit", 0, "Fit to thin, immature, weakly arbitraged markets on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&executability, "executability", 0, "Executability on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&evidenceQuality, "evidence-quality", 0, "Evidence quality on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&basinRepetitionPenalty, "basin-repetition-penalty", 0, "Penalty for repeated-basin rediscovery on a 0-10 scale")
	scoreCmd.Flags().Float64Var(&genericDragPenalty, "generic-drag-penalty", 0, "Penalty for generic microstructure drag on a 0-10 scale")
	scoreCmd.Flags().StringVar(&notes, "notes", "", "Optional scoring notes")
	_ = scoreCmd.MarkFlagRequired("hypothesis-id")

	var topSessionID string
	var topLimit int
	topCmd := &cobra.Command{
		Use:   "top",
		Short: "Show the best currently scored hypotheses for a session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.StoreDB, `
WITH latest_scores AS (
  SELECT *
  FROM (
    SELECT
      hs.*,
      ROW_NUMBER() OVER (PARTITION BY hs.hypothesis_id ORDER BY hs.created_at DESC, hs.score_id DESC) AS rn
    FROM hypothesis_scores hs
  )
  WHERE rn = 1
)
SELECT
  h.hypothesis_id,
  h.title,
  h.target_market,
  h.status,
  ls.objective_score,
  ls.surprise_score,
  ls.posterior_novelty,
  ls.posterior_plausibility,
  ls.thin_market_fit,
  ls.executability,
  ls.evidence_quality,
  ls.lead_id,
  ls.paper_id,
  ls.result_id,
  ls.created_at AS scored_at
FROM hypotheses h
LEFT JOIN latest_scores ls ON ls.hypothesis_id = h.hypothesis_id
WHERE h.session_id = ?
ORDER BY COALESCE(ls.objective_score, -999) DESC, h.created_at DESC
LIMIT ?`, topSessionID, topLimit)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("hypothesis_top", items)
			return emitAndStore(cmd, "hypothesis_top", summary, map[string]any{"items": items}, len(items), map[string]any{"session_id": topSessionID, "limit": topLimit})
		},
	}
	topCmd.Flags().StringVar(&topSessionID, "session-id", "", "Session ID")
	topCmd.Flags().IntVar(&topLimit, "limit", 10, "Maximum hypotheses to return")
	_ = topCmd.MarkFlagRequired("session-id")

	hypCmd.AddCommand(addCmd, listCmd, scoreCmd, topCmd)
	return hypCmd
}

func clampScore(value float64) float64 {
	return math.Max(0, math.Min(10, value))
}

func computeSurpriseScore(input core.HypothesisScoreInput) float64 {
	noveltyShift := math.Abs(input.PosteriorNovelty - input.PriorNovelty)
	plausibilityShift := math.Abs(input.PosteriorPlausibility - input.PriorPlausibility)
	return clampScore((noveltyShift + plausibilityShift) / 2.0)
}

func computeObjectiveScore(input core.HypothesisScoreInput) float64 {
	positive := (0.22 * input.SurpriseScore) +
		(0.18 * input.PosteriorNovelty) +
		(0.20 * input.PosteriorPlausibility) +
		(0.16 * input.ThinMarketFit) +
		(0.14 * input.Executability) +
		(0.10 * input.EvidenceQuality)
	negative := (0.10 * input.BasinRepetitionPenalty) + (0.10 * input.GenericDragPenalty)
	return positive - negative
}
