package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newNoteCommand() *cobra.Command {
	noteCmd := &cobra.Command{
		Use:   "note",
		Short: "Store research notes on a session",
	}

	var sessionID string
	var kind string
	var text string
	var paperID string
	var resultID string

	addCmd := &cobra.Command{
		Use:   "add",
		Short: "Add a note to a session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			noteID, err := core.SaveNote(runtime.StoreDB, sessionID, kind, text, paperID, resultID)
			if err != nil {
				return err
			}
			summary := fmt.Sprintf("note saved: note_id=%s session_id=%s", noteID, sessionID)
			payload := map[string]any{"note_id": noteID, "session_id": sessionID, "kind": kind, "text": text, "paper_id": paperID, "result_id": resultID}
			return emitAndStore(cmd, "note_add", summary, payload, 1, payload)
		},
	}
	addCmd.Flags().StringVar(&sessionID, "session-id", "", "Session ID")
	addCmd.Flags().StringVar(&kind, "kind", "observation", "Note kind")
	addCmd.Flags().StringVar(&text, "text", "", "Note text")
	addCmd.Flags().StringVar(&paperID, "paper-id", "", "Optional linked paper ID")
	addCmd.Flags().StringVar(&resultID, "result-id", "", "Optional linked result ID")
	_ = addCmd.MarkFlagRequired("session-id")
	_ = addCmd.MarkFlagRequired("text")

	var listSessionID string
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List notes for a session",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			items, err := core.QueryRows(runtime.StoreDB, `SELECT note_id, kind, text, paper_id, result_id, created_at FROM notes WHERE session_id = ? ORDER BY created_at DESC LIMIT 100`, listSessionID)
			if err != nil {
				return err
			}
			summary := core.SummarizeList("notes", items)
			return emitAndStore(cmd, "note_list", summary, map[string]any{"items": items}, len(items), map[string]any{"session_id": listSessionID})
		},
	}
	listCmd.Flags().StringVar(&listSessionID, "session-id", "", "Session ID")
	_ = listCmd.MarkFlagRequired("session-id")

	noteCmd.AddCommand(addCmd, listCmd)
	return noteCmd
}
