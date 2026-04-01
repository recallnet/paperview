package app

import (
	"database/sql"
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newSessionCommand() *cobra.Command {
	sessionCmd := &cobra.Command{
		Use:   "session",
		Short: "Create and inspect mdream sessions",
	}

	var label string
	var prompt string
	createCmd := &cobra.Command{
		Use:   "create",
		Short: "Create a new mdream session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			sessionID, err := core.CreateSession(runtime.StoreDB, label, prompt, runtime.SourcePath)
			if err != nil {
				return err
			}
			summary := fmt.Sprintf("session created: session_id=%s", sessionID)
			payload := map[string]any{
				"session_id": sessionID,
				"label":      label,
				"prompt":     prompt,
			}
			return emitAndStore(cmd, "session_create", summary, payload, 1, map[string]any{
				"label":  label,
				"prompt": prompt,
			})
		},
	}
	createCmd.Flags().StringVar(&label, "label", "", "Human label for the research session")
	createCmd.Flags().StringVar(&prompt, "prompt", "", "Initial research prompt")

	var getSessionID string
	getCmd := &cobra.Command{
		Use:   "get",
		Short: "Get one session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.StoreDB, `SELECT session_id, label, prompt, status, source_db_path, created_at FROM sessions WHERE session_id = ?`, getSessionID)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("session", items)
			return emitAndStore(cmd, "session_get", summary, map[string]any{"items": items}, len(items), map[string]any{"session_id": getSessionID})
		},
	}
	getCmd.Flags().StringVar(&getSessionID, "session-id", "", "Session ID")
	_ = getCmd.MarkFlagRequired("session-id")

	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List recent sessions",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.StoreDB, `SELECT session_id, label, status, created_at FROM sessions ORDER BY created_at DESC LIMIT 100`)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("sessions", items)
			return emitAndStore(cmd, "session_list", summary, map[string]any{"items": items}, len(items), map[string]any{})
		},
	}

	sessionCmd.AddCommand(createCmd, getCmd, listCmd)
	return sessionCmd
}

func mustOneRow(items []map[string]any, label string) error {
	if len(items) == 0 {
		return sql.ErrNoRows
	}
	if len(items) > 1 {
		return fmt.Errorf("%s returned more than one row", label)
	}
	return nil
}
