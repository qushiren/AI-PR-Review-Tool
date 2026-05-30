from ai_pr_review_tool.diff_parser import added_lines
from ai_pr_review_tool.schemas import ChangedFile


def test_added_lines_preserve_new_line_numbers() -> None:
    changed_file = ChangedFile(
        filename="app.py",
        status="modified",
        additions=2,
        deletions=1,
        changes=3,
        patch="""@@ -10,3 +10,4 @@ def run():
 context()
-old_call()
+new_call()
+return True
""",
    )

    lines = added_lines(changed_file)

    assert [line.line_no for line in lines] == [11, 12]
    assert [line.text for line in lines] == ["new_call()", "return True"]
