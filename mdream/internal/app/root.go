package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func NewRootCommand() (*cobra.Command, error) {
	var storeDBPath string
	var sourceDBPath string
	var jsonOutput bool
	var fullOutput bool
	var page int
	var pageSize int
	var sessionID string

	root := &cobra.Command{
		Use:   "mdream",
		Short: "Local research-agent CLI over the paperview literature store",
		PersistentPreRunE: func(cmd *cobra.Command, _ []string) error {
			output := core.OutputOptions{
				JSON:     jsonOutput,
				Full:     fullOutput,
				Page:     page,
				PageSize: pageSize,
				Session:  sessionID,
			}
			runtime, err := core.OpenRuntime(storeDBPath, sourceDBPath, output)
			if err != nil {
				return err
			}
			cmd.SetContext(core.WithRuntime(cmd.Context(), runtime))
			return nil
		},
		PersistentPostRunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return nil
			}
			return runtime.Close()
		},
	}

	root.PersistentFlags().StringVar(&storeDBPath, "store-db", "", "Path to the mdream session/result SQLite store")
	root.PersistentFlags().StringVar(&sourceDBPath, "source-db", "", "Path to the paperview source SQLite store")
	root.PersistentFlags().BoolVar(&jsonOutput, "json", false, "Emit machine-readable JSON")
	root.PersistentFlags().BoolVar(&fullOutput, "full", false, "Emit full stored payload instead of the short summary view")
	root.PersistentFlags().IntVar(&page, "page", 1, "Page number for list and stored result output")
	root.PersistentFlags().IntVar(&pageSize, "page-size", 5, "Page size for list and stored result output")
	root.PersistentFlags().StringVar(&sessionID, "session", "", "Attach the command result to an existing mdream session")

	root.AddCommand(newInitCommand())
	root.AddCommand(newSessionCommand())
	root.AddCommand(newNoteCommand())
	root.AddCommand(newHypothesisCommand())
	root.AddCommand(newSearchCommand())
	root.AddCommand(newPaperCommand())
	root.AddCommand(newSurfaceCommand())
	root.AddCommand(newScoreCommand())
	root.AddCommand(newResultCommand())
	root.AddCommand(newToolsCommand())

	return root, nil
}

func emitAndStore(cmd *cobra.Command, kind string, summary string, payload map[string]any, totalItems int, args map[string]any) error {
	runtime, err := core.RuntimeFromContext(cmd.Context())
	if err != nil {
		return err
	}
	resultID, err := core.SaveQueryResult(runtime.StoreDB, runtime.Output.Session, commandPath(cmd), args, kind, summary, payload, totalItems)
	if err != nil {
		return err
	}
	stored := core.BuildStoredResult(resultID, commandPath(cmd), runtime.Output.Session, summary, kind, payload, totalItems, runtime.Output)
	text, err := core.RenderStoredResult(stored, runtime.Output)
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.OutOrStdout(), text)
	return nil
}

func commandPath(cmd *cobra.Command) string {
	return cmd.CommandPath()
}
