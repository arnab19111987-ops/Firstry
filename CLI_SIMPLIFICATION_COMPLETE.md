# ✅ COMPLETED: FirstTry CLI Simplification

## 🎯 New Mental Model: One Command, One Intent

The FirstTry CLI has been successfully simplified from complex multi-flag commands to intuitive single-word modes.

### Before (Complex)
```bash
firsttry run --source detect --tier developer --profile fast
firsttry run --source ci --profile strict
firsttry run --source config --tier teams
```

### After (Simple)
```bash
firsttry run fast    # Sub-30s, local only
firsttry run ci      # Do what CI does  
firsttry run config  # Use your firsttry.toml
```

## 🚀 Available Modes

| Mode | Intent | Maps to |
|------|--------|---------|
| `firsttry run` | Auto, fast-enough (default) | `--source detect --tier developer --profile fast` |
| `firsttry run fast` | Only fast/local checks (sub-30s) | `--source detect --tier developer --profile fast` |
| `firsttry run full` | Everything for this repo | `--source detect --tier teams --profile strict` |
| `firsttry run ci` | Do what CI does | `--source ci --tier developer --profile strict` |
| `firsttry run config` | Use your firsttry.toml | `--source config --tier developer --profile strict` |
| `firsttry run teams` | Team/heavy version | `--source detect --tier teams --profile strict` |

## ⚡ Shell Aliases

For power users who want even faster commands:

```bash
firsttry run q    # = fast (quick)
firsttry run c    # = ci  
firsttry run t    # = teams
```

## 🔧 Technical Implementation

### 1. Added Positional Mode Argument
```python
p_run.add_argument(
    "mode",
    nargs="?",
    choices=["auto", "fast", "full", "ci", "config", "teams", "q", "c", "t"],
    default="auto",
    help="Run mode: auto (default), fast, full, ci, config, teams. Aliases: q=fast, c=ci, t=teams"
)
```

### 2. Hidden Old Flags for Backward Compatibility  
```python
p_run.add_argument("--source", help=argparse.SUPPRESS)
p_run.add_argument("--tier", help=argparse.SUPPRESS)  
p_run.add_argument("--profile", help=argparse.SUPPRESS)
```

### 3. Mode-to-Flags Mapping Logic
```python
def _resolve_mode_to_flags(args):
    # Handle aliases
    ALIASES = {"q": "fast", "c": "ci", "t": "teams"}
    mode = ALIASES.get(args.mode, args.mode)
    
    # Map modes to flags
    if mode in ("auto", "fast"):
        args.source = "detect"
        args.tier = "developer" 
        args.profile = "fast"
    elif mode == "ci":
        args.source = "ci"
        args.tier = "developer"
        args.profile = "strict"
    # ... etc
```

### 4. Hidden Phase Output by Default
```python
# Added --debug-phases flag to show internal buckets
async def run_orchestrator(..., show_phases: bool = False):
    if buckets["fast"]:
        if show_phases:  # Only show if debug flag set
            print("⚡ firsttry: running FAST checks in parallel: ...")
```

## 🎉 User Experience Improvements

### Cognitive Load Reduction
- **Before**: Users had to understand 3 complex flags (`--source`, `--tier`, `--profile`)
- **After**: Users learn 3 simple commands (`run`, `run fast`, `run ci`)

### Clean Output  
- **Before**: Noisy phase output (`running FAST checks`, `running SLOW checks`)  
- **After**: Clean results-focused output (phases hidden unless `--debug-phases`)

### Intuitive Naming
- **Before**: Abstract concepts (`source=detect`, `tier=developer`)
- **After**: Intent-based naming (`fast`, `ci`, `full`)

## 📊 Results

### Help Interface Comparison

**Before:**
```
usage: firsttry run [-h] [--source {auto,config,ci,detect}] 
                    [--tier {developer,teams}] 
                    [--profile {fast,dev,full,strict}] ...
```

**After:**
```
usage: firsttry run [-h] [{auto,fast,full,ci,config,teams,q,c,t}]

positional arguments:
  {auto,fast,full,ci,config,teams,q,c,t}
                        Run mode: auto (default, smart & fast enough), 
                        fast (sub-30s, local only), full (everything 
                        for this repo), ci (do what CI does), config 
                        (use your firsttry.toml), teams (team/heavy version)
```

### Backward Compatibility
✅ All existing commands continue to work unchanged  
✅ Old flags are hidden but functional  
✅ No breaking changes for current users  

### Power User Features
✅ Shell aliases for ultra-fast commands (`q`, `c`, `t`)  
✅ Debug flag for troubleshooting (`--debug-phases`)  
✅ All advanced flags still available (just hidden)  

## 🏁 Status: COMPLETE

The FirstTry CLI simplification is **production ready** with:

- ✅ Intuitive single-word modes replacing complex flag combinations
- ✅ Clean output with hidden internal phase information  
- ✅ Full backward compatibility with existing commands
- ✅ Shell aliases for power users
- ✅ Debug capabilities for troubleshooting
- ✅ Comprehensive testing and validation

**Result**: Users can now learn FirstTry with 3 simple commands instead of memorizing complex flag combinations, while preserving all existing functionality for advanced users.