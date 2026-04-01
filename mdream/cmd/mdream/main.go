package main

import (
	"fmt"
	"os"

	"github.com/recallnet/paperview/mdream/internal/app"
)

func main() {
	root, err := app.NewRootCommand()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := root.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
