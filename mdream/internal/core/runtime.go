package core

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type contextKey string

const runtimeContextKey contextKey = "mdream_runtime"

type OutputOptions struct {
	JSON     bool
	Full     bool
	Page     int
	PageSize int
	Session  string
}

type Runtime struct {
	StorePath  string
	SourcePath string
	StoreDB    *sql.DB
	SourceDB   *sql.DB
	Output     OutputOptions
}

func WithRuntime(ctx context.Context, runtime *Runtime) context.Context {
	return context.WithValue(ctx, runtimeContextKey, runtime)
}

func RuntimeFromContext(ctx context.Context) (*Runtime, error) {
	runtime, ok := ctx.Value(runtimeContextKey).(*Runtime)
	if !ok || runtime == nil {
		return nil, errors.New("mdream runtime missing from context")
	}
	return runtime, nil
}

func DefaultRepoRoot() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	dir := cwd
	for {
		if fileExists(filepath.Join(dir, "package.json")) &&
			fileExists(filepath.Join(dir, "docs", "briefings", "2026-03-25-structural-analogy-engine-plan.md")) {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", errors.New("could not locate paperview repo root")
		}
		dir = parent
	}
}

func DefaultStorePath() (string, error) {
	root, err := DefaultRepoRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(root, "mdream", "mdream.sqlite3"), nil
}

func DefaultSourcePath() (string, error) {
	root, err := DefaultRepoRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(root, "data", "structural-analogy", "paperview.sqlite3"), nil
}

func OpenRuntime(storePath string, sourcePath string, output OutputOptions) (*Runtime, error) {
	if storePath == "" {
		defaultStore, err := DefaultStorePath()
		if err != nil {
			return nil, err
		}
		storePath = defaultStore
	}
	if sourcePath == "" {
		defaultSource, err := DefaultSourcePath()
		if err != nil {
			return nil, err
		}
		sourcePath = defaultSource
	}
	if output.Page < 1 {
		output.Page = 1
	}
	if output.PageSize < 1 {
		output.PageSize = 5
	}
	if output.PageSize > 50 {
		output.PageSize = 50
	}

	if err := os.MkdirAll(filepath.Dir(storePath), 0o755); err != nil {
		return nil, err
	}
	storeDB, err := sql.Open("sqlite3", fmt.Sprintf("file:%s?_busy_timeout=5000&_foreign_keys=on", storePath))
	if err != nil {
		return nil, err
	}
	sourceDB, err := sql.Open("sqlite3", fmt.Sprintf("file:%s?mode=ro&_query_only=1&_busy_timeout=5000", sourcePath))
	if err != nil {
		_ = storeDB.Close()
		return nil, err
	}
	runtime := &Runtime{
		StorePath:  storePath,
		SourcePath: sourcePath,
		StoreDB:    storeDB,
		SourceDB:   sourceDB,
		Output:     output,
	}
	if err := EnsureStoreSchema(storeDB); err != nil {
		_ = storeDB.Close()
		_ = sourceDB.Close()
		return nil, err
	}
	if err := UpsertSetting(storeDB, "source_db_path", sourcePath); err != nil {
		_ = storeDB.Close()
		_ = sourceDB.Close()
		return nil, err
	}
	return runtime, nil
}

func (runtime *Runtime) Close() error {
	var errs []string
	if runtime.StoreDB != nil {
		if err := runtime.StoreDB.Close(); err != nil {
			errs = append(errs, err.Error())
		}
	}
	if runtime.SourceDB != nil {
		if err := runtime.SourceDB.Close(); err != nil {
			errs = append(errs, err.Error())
		}
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}
