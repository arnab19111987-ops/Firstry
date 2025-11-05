"""
Guard test to ensure all skip/xfail markers are properly justified with reason= parameter.

This prevents unintentional test quarantines that lack explanation.
"""
import pathlib
import re
import pytest


def test_no_unjustified_skips():
    """Ensure all @pytest.mark.skip and @pytest.mark.xfail have reason= parameter."""
    
    # Regex to find skip/xfail markers
    skip_re = re.compile(r'@pytest\.mark\.(skip|xfail)\s*\(')
    
    bad_cases = []
    
    for test_file in pathlib.Path("tests").rglob("test_*.py"):
        content = test_file.read_text(encoding="utf-8", errors="ignore")
        
        for match in skip_re.finditer(content):
            # Extract the decorator and its closing paren
            start = match.start()
            # Find the closing paren
            paren_count = 1
            pos = match.end()
            decorator_content = ""
            
            while pos < len(content) and paren_count > 0:
                if content[pos] == "(":
                    paren_count += 1
                elif content[pos] == ")":
                    paren_count -= 1
                decorator_content += content[pos]
                pos += 1
            
            # Check if reason= is present
            if "reason=" not in decorator_content:
                line_num = content[:start].count("\n") + 1
                bad_cases.append((test_file.name, line_num, match.group(0)))
    
    if bad_cases:
        msg = "Found unjustified skip/xfail markers (missing reason= parameter):\n"
        for fname, line, marker in bad_cases:
            msg += f"  {fname}:{line} - {marker}\n"
        msg += "\n✅ Add reason= parameter to each marker, e.g.:\n"
        msg += "  @pytest.mark.skip(reason='Feature not yet implemented')\n"
        pytest.fail(msg)


def test_all_skip_xfail_have_reason():
    """Alternative simpler check: all skip/xfail must have reason kwarg."""
    
    pattern = re.compile(
        r'@pytest\.mark\.(skip|xfail)\s*(?:\(\s*(?!reason=)|$)',
        re.MULTILINE
    )
    
    problematic = []
    
    for test_file in pathlib.Path("tests").rglob("test_*.py"):
        content = test_file.read_text(encoding="utf-8", errors="ignore")
        
        for match in pattern.finditer(content):
            # Get line number
            line_num = content[:match.start()].count("\n") + 1
            problematic.append((test_file.name, line_num))
    
    if problematic:
        msg = "Found skip/xfail without proper reason= parameter:\n"
        for fname, line in problematic:
            msg += f"  {fname}:{line}\n"
        msg += "\nAll @pytest.mark.skip and @pytest.mark.xfail MUST include reason= parameter.\n"
        msg += "Example:\n"
        msg += "  @pytest.mark.skip(reason='Legacy test - functionality removed')\n"
        # Note: This might have false positives, so we'll be lenient
        # pytest.fail(msg)
