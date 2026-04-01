package app

import (
	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newResultCommand() *cobra.Command {
	resultCmd := &cobra.Command{
		Use:   "result",
		Short: "Reload stored results by ID",
	}

	var resultID string
	getCmd := &cobra.Command{
		Use:   "get",
		Short: "Reload a stored result by ID",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			stored, err := core.LoadQueryResult(runtime.StoreDB, resultID)
			if err != nil {
				return err
			}
			rebuilt := core.BuildStoredResult(stored.ResultID, stored.Command, stored.SessionID, stored.Summary, stored.Kind, stored.Data, stored.TotalItems, runtime.Output)
			text, err := core.RenderStoredResult(rebuilt, runtime.Output)
			if err != nil {
				return err
			}
			_, err = cmd.OutOrStdout().Write([]byte(text + "\n"))
			return err
		},
	}
	getCmd.Flags().StringVar(&resultID, "result-id", "", "Stored result ID")
	_ = getCmd.MarkFlagRequired("result-id")

	resultCmd.AddCommand(getCmd)
	return resultCmd
}
