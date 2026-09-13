package custom

import (
	"encoding/json"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

// This test is installed only in the isolated, pinned source snapshot.
func TestBaselineInventory(t *testing.T) {
	fset := token.NewFileSet()
	pkgs, err := parser.ParseDir(fset, ".", func(info os.FileInfo) bool {
		return !strings.HasSuffix(info.Name(), "_test.go")
	}, 0)
	if err != nil {
		t.Fatal(err)
	}
	getters := map[string]any{}
	registry := map[string]string{}
	definitions := []any{}
	for _, f := range pkgs["custom"].Files {
		ast.Inspect(f, func(n ast.Node) bool {
			lit, ok := n.(*ast.CompositeLit)
			if !ok {
				return true
			}
			id, ok := lit.Type.(*ast.Ident)
			if !ok || id.Name != "CustomExtractor" {
				return true
			}
			definitions = append(definitions, map[string]any{"path": "internal/extractors/custom/" + filepath.Base(fset.Position(lit.Pos()).Filename), "line": fset.Position(lit.Pos()).Line})
			return true
		})
		for _, d := range f.Decls {
			fn, ok := d.(*ast.FuncDecl)
			if !ok {
				continue
			}
			if fn.Name.Name == "buildAllExtractors" {
				ast.Inspect(fn, func(n ast.Node) bool {
					kv, ok := n.(*ast.KeyValueExpr)
					if !ok {
						return true
					}
					key, ok := kv.Key.(*ast.BasicLit)
					if !ok {
						return true
					}
					call, ok := kv.Value.(*ast.CallExpr)
					if !ok {
						return true
					}
					id, ok := call.Fun.(*ast.Ident)
					if ok {
						registry[strings.Trim(key.Value, "\"")] = id.Name
					}
					return true
				})
			}
			if fn.Type.Results == nil || len(fn.Type.Results.List) != 1 {
				continue
			}
			ptr, ok := fn.Type.Results.List[0].Type.(*ast.StarExpr)
			if !ok {
				continue
			}
			id, ok := ptr.X.(*ast.Ident)
			if !ok || id.Name != "CustomExtractor" {
				continue
			}
			getters[fn.Name.Name] = map[string]any{
				"path":     "internal/extractors/custom/" + filepath.Base(fset.Position(fn.Pos()).Filename),
				"line":     fset.Position(fn.Pos()).Line,
				"end_line": fset.Position(fn.End()).Line,
			}
		}
	}
	sites := map[string]any{}
	for name, e := range buildAllExtractors() {
		fields := map[string]any{}
		v := reflect.ValueOf(e).Elem()
		typ := v.Type()
		for i := 0; i < v.NumField(); i++ {
			if typ.Field(i).Name != "Content" {
				fields[typ.Field(i).Name] = v.Field(i).Interface()
			}
		}
		functionBearing := false
		if e.Content != nil {
			transforms := map[string]any{}
			for selector, transform := range e.Content.Transforms {
				switch x := transform.(type) {
				case *StringTransform:
					transforms[selector] = map[string]any{"kind": "string", "target_tag": x.TargetTag}
				case *FunctionTransform:
					functionBearing = true
					fn := runtime.FuncForPC(reflect.ValueOf(x.Fn).Pointer())
					file, line := fn.FileLine(fn.Entry())
					transforms[selector] = map[string]any{"kind": "function", "symbol": fn.Name(), "path": "internal/extractors/custom/" + filepath.Base(file), "line": line}
				default:
					t.Fatalf("unhandled transform %T", transform)
				}
			}
			fields["Content"] = map[string]any{"selectors": e.Content.Selectors, "clean": e.Content.Clean, "transforms": transforms, "disable_default_cleaner": e.Content.DisableDefaultCleaner}
		}
		sites[name] = map[string]any{"getter": registry[name], "source": getters[registry[name]], "configuration": fields, "function_bearing": functionBearing}
	}
	domains := map[string]string{}
	for domain, extractor := range buildDomainMap(buildAllExtractors()) {
		domains[domain] = extractor.Domain
	}
	b, err := json.MarshalIndent(map[string]any{"sites": sites, "getters": getters, "definitions": definitions, "resolved_domains": domains}, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("BASELINE_INVENTORY"), append(b, '\n'), 0644); err != nil {
		t.Fatal(err)
	}
}
