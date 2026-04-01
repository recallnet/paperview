package app

import (
	"fmt"

	"github.com/recallnet/paperview/mdream/internal/core"
	"github.com/spf13/cobra"
)

func newInitCommand() *cobra.Command {
	return &cobra.Command{
		Use:   "init",
		Short: "Initialize the mdream local session store",
		RunE: func(cmd *cobra.Command, _ []string) error {
			runtime, err := core.RuntimeFromContext(cmd.Context())
			if err != nil {
				return err
			}
			summary := fmt.Sprintf("mdream store ready. store_db=%s source_db=%s", runtime.StorePath, runtime.SourcePath)
			payload := map[string]any{
				"store_db":  runtime.StorePath,
				"source_db": runtime.SourcePath,
			}
			return emitAndStore(cmd, "init", summary, payload, 0, map[string]any{
				"store_db":  runtime.StorePath,
				"source_db": runtime.SourcePath,
			})
		},
	}
}
