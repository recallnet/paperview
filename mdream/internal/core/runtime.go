package core

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type contextKey string

const runtimeContextKey contextKey = "mdream_runtime"

const (
	envStorePath  = "MDREAM_STORE_DB"
	envSourcePath = "MDREAM_SOURCE_DB"
)

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
	if envPath := strings.TrimSpace(os.Getenv(envStorePath)); envPath != "" {
		return envPath, nil
	}
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(configDir, "mdream", "mdream.sqlite3"), nil
}

func DefaultSourcePath(storeDB *sql.DB) (string, error) {
	if envPath := strings.TrimSpace(os.Getenv(envSourcePath)); envPath != "" {
		return envPath, nil
	}
	// @context decision Resolve the source DB from the persisted store setting
	// before falling back to repo discovery. This is what lets an installed
	// mdream binary keep working from arbitrary directories after one successful
	// repo-backed run seeds the canonical corpus path.
	if storeDB != nil {
		if storedPath, err := LoadSetting(storeDB, "source_db_path"); err == nil && strings.TrimSpace(storedPath) != "" {
			return storedPath, nil
		}
	}
	root, err := DefaultRepoRoot()
	if err != nil {
		return "", errors.New("could not resolve source db path; set MDREAM_SOURCE_DB or run mdream once inside the paperview repo")
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
	if err := os.MkdirAll(filepath.Dir(storePath), 0o755); err != nil {
		return nil, err
	}
	if err := maybeMigrateLegacyStore(storePath); err != nil {
		return nil, err
	}

	if err := os.MkdirAll(filepath.Dir(storePath), 0o755); err != nil {
		return nil, err
	}
	storeDB, err := sql.Open("sqlite3", fmt.Sprintf("file:%s?_busy_timeout=5000&_foreign_keys=on", storePath))
	if err != nil {
		return nil, err
	}
	if err := EnsureStoreSchema(storeDB); err != nil {
		_ = storeDB.Close()
		return nil, err
	}

	if sourcePath == "" {
		defaultSource, err := DefaultSourcePath(storeDB)
		if err != nil {
			_ = storeDB.Close()
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
	if !fileExists(sourcePath) {
		_ = storeDB.Close()
		return nil, fmt.Errorf("source db does not exist: %s", sourcePath)
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

func maybeMigrateLegacyStore(targetStorePath string) error {
	if fileExists(targetStorePath) {
		return nil
	}
	root, err := DefaultRepoRoot()
	if err != nil {
		return nil
	}
	legacyPath := filepath.Join(root, "mdream", "mdream.sqlite3")
	if !fileExists(legacyPath) || legacyPath == targetStorePath {
		return nil
	}
	// @context history The CLI originally stored session state under repo-local
	// `mdream/mdream.sqlite3`. Copy that file forward the first time we open the
	// machine-global store so installs from arbitrary directories still see the
	// same prior sessions and source-path settings.
	return copyFile(legacyPath, targetStorePath)
}

func copyFile(sourcePath string, targetPath string) error {
	source, err := os.Open(sourcePath)
	if err != nil {
		return err
	}
	defer source.Close()

	target, err := os.Create(targetPath)
	if err != nil {
		return err
	}
	defer target.Close()

	if _, err := io.Copy(target, source); err != nil {
		return err
	}
	return target.Close()
}
