---
this_file: PLAN-102.md
---

# Plan — Issue 102: GitNextVer Integration & Simplification

## Scope (Single Sentence)
Integrate a simplified 80-line version of the gitnextver tool as a core vexy-overnight utility, reducing complexity from 448 lines while maintaining semantic versioning functionality.

## Research Notes
- **Original Analysis**: Complex 448-line script with enterprise features (GitPython compatibility hacks, elaborate error handling, stash management)
- **Simplification Target**: Reduce to ~80 lines using subprocess calls instead of GitPython
- **Package Research**: Replace heavy dependencies (GitPython, Rich, Fire, Loguru) with stdlib-only implementation
- **Architecture Decision**: Integrate as `src/vexy_overnight/tools/version_bump.py` rather than external script

## Technical Decisions
- **Subprocess Over Libraries**: Use direct `git` commands via `subprocess.run()` to eliminate GitPython compatibility issues
- **Minimal Dependencies**: No external packages beyond testing requirements
- **Simple Error Handling**: Basic try/catch with clear error messages, no enterprise recovery mechanisms
- **Package Integration**: Add as tool in existing package structure with CLI entry point
- **Test-First Development**: Comprehensive unit tests with mocked subprocess calls

## Phase Breakdown

### Phase 1 — Foundation Setup
- Create `src/vexy_overnight/tools/` directory structure
- Add `__init__.py` files for proper package imports
- Set up entry points in `pyproject.toml` for CLI access
- Configure test structure for new tools module

### Phase 2 — Core Implementation
- **File**: `src/vexy_overnight/tools/version_bump.py` (~80 lines)
- **Functions**:
  - `is_git_repo() -> bool` - Check for .git directory
  - `get_next_version() -> str` - Parse git tags, increment patch
  - `check_clean_working_tree() -> bool` - Verify no uncommitted changes
  - `bump_version() -> None` - Main orchestration function
- **Strategy**: Subprocess calls for all git operations, simple error handling

### Phase 3 — CLI Integration
- Add version-bump command to main CLI interface
- Configure entry point in pyproject.toml
- Implement basic argument parsing for optional verbose flag
- Add help text and usage examples

### Phase 4 — Testing Implementation
- **File**: `tests/test_version_bump.py`
- **Coverage Target**: 95% line coverage
- **Test Cases**:
  - Version parsing with no tags (default v1.0.0)
  - Version parsing with existing tags (increment patch)
  - Git repository detection (valid/invalid)
  - Clean working tree detection
  - Full integration workflow
- **Mocking Strategy**: Mock all subprocess calls for deterministic testing

### Phase 5 — Documentation & Polish
- Update README.md with version-bump tool usage
- Add examples and common workflows
- Update CHANGELOG.md with new feature
- Create migration guide from external gitnextver

## Implementation Details

### Core Algorithm
```python
def get_next_version() -> str:
    """Get next patch version based on existing tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*.*.*"],
            capture_output=True, text=True, check=True
        )
        tags = [t.strip() for t in result.stdout.split() if t.strip()]

        if not tags:
            return "v1.0.0"

        # Find highest version
        latest = max(tags, key=lambda t: tuple(map(int, t[1:].split('.'))))
        major, minor, patch = map(int, latest[1:].split('.'))
        return f"v{major}.{minor}.{patch + 1}"
    except:
        return "v1.0.0"
```

### Error Handling Pattern
```python
try:
    subprocess.run(["git", "command"], check=True, capture_output=True)
except subprocess.CalledProcessError:
    print("Error: Git operation failed")
    sys.exit(1)
```

### Git Operations
- **Repository Check**: `(Path.cwd() / ".git").exists()`
- **Status Check**: `git status --porcelain`
- **Tag Listing**: `git tag -l "v*.*.*"`
- **Tag Creation**: `git tag {version}`
- **Remote Push**: `git push && git push --tags`

## Testing Strategy

### Unit Tests
- Mock all subprocess.run() calls
- Test edge cases: empty repos, malformed tags, network failures
- Verify version calculation logic with various tag patterns
- Test error conditions and appropriate exit codes

### Integration Tests
- Test with real git repositories in temporary directories
- Verify actual tag creation and listing
- Test workflow with clean and dirty working trees
- Cross-platform validation

### Performance Benchmarks
- Execution time < 2 seconds for typical operations
- Memory usage < 10MB
- Startup time < 500ms

## Dependencies Analysis

### Removed Dependencies (from original)
- **GitPython**: 6.8k stars, but adds complexity and compatibility issues
- **Rich**: 49k stars, overkill for simple status messages
- **Fire**: 27k stars, argparse sufficient for simple CLI
- **Loguru**: 19k stars, print statements adequate for tool output

### Kept Dependencies
- **Standard Library Only**: subprocess, pathlib, sys, argparse
- **Testing**: pytest, pytest-cov (existing)

### Justification
1. **Reduced Complexity**: Fewer dependencies = less maintenance
2. **Better Reliability**: Direct git commands more stable than library wrappers
3. **Improved Performance**: No library overhead, faster startup
4. **Easier Testing**: Mock subprocess calls simpler than complex library objects

## Risk Assessment

### Technical Risks
**Risk**: Subprocess calls fail in different environments
**Mitigation**: Cross-platform testing, clear error messages

**Risk**: Git command interface changes
**Mitigation**: Use well-established git commands, version checks

### User Experience Risks
**Risk**: Feature parity concerns from complex version
**Mitigation**: Document deliberate simplifications, focus on 80% use case

## Success Metrics

### Code Reduction
- 448 lines → 80 lines (82% reduction)
- 4 external dependencies → 0
- Complex error handling → Simple error messages

### Quality Metrics
- Test coverage >95%
- Performance <2s execution time
- Zero external package dependencies
- Cross-platform compatibility

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep existing external/utils/gitnextver
- Implement new simplified version
- Add feature comparison documentation

### Phase 2: Testing & Validation
- Run both versions in parallel
- Compare outputs and performance
- Gather user feedback on simplified interface

### Phase 3: Replacement
- Update documentation to reference new version
- Deprecate external script usage
- Provide migration guide

### Phase 4: Cleanup
- Remove external/utils/gitnextver
- Clean up unused complex code
- Update package metadata

## Exit Criteria
- Simplified version-bump tool integrated in package structure
- CLI command accessible via pyproject.toml entry point
- Comprehensive test suite with >95% coverage
- Documentation updated with usage examples
- Performance benchmarks meet targets (<2s execution)
- Zero external dependencies beyond testing framework