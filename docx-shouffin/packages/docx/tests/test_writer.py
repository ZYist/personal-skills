import base64
import json
from pathlib import Path

from docx import Document

from main import markdown_to_docx, parse_write_options


def test_markdown_to_docx_writes_headings_table_image_and_code_block(tmp_path: Path):
    markdown_path = tmp_path / "report.md"
    docx_path = tmp_path / "report.docx"
    image_path = tmp_path / "demo.png"

    image_path.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII="
        )
    )
    markdown_path.write_text(
        "# 标题\n\n"
        "正文含 **加粗**、*斜体*、~~删除线~~ 和 `code`。\n\n"
        "> 引用\n\n"
        "- 列表项\n\n"
        "---\n\n"
        "```python\nprint('hi')\n```\n\n"
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
        f"![示例图]({image_path.name})\n",
        encoding="utf-8",
    )

    markdown_to_docx(markdown_path, docx_path)

    document = Document(docx_path)

    assert docx_path.exists()
    assert any(paragraph.text == "标题" for paragraph in document.paragraphs)
    assert any(paragraph.text == "引用" for paragraph in document.paragraphs)
    assert any(paragraph.text == "列表项" for paragraph in document.paragraphs)
    assert any("print('hi')" in paragraph.text for paragraph in document.paragraphs)
    assert len(document.tables) == 1
    assert document.tables[0].cell(0, 0).text == "A"
    assert document.tables[0].cell(1, 1).text == "2"
    assert len(document.inline_shapes) == 1

    content_paragraph = next(
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.startswith("正文含")
    )
    run_states = {
        run.text: (run.bold, run.italic, run.font.strike)
        for run in content_paragraph.runs
    }

    assert run_states["加粗"] == (True, False, False)
    assert run_states["斜体"] == (False, True, False)
    assert run_states["删除线"] == (False, False, True)


def test_cli_style_overrides_json_config(tmp_path: Path):
    config_path = tmp_path / "style.json"
    config_path.write_text(
        json.dumps({"body": {"size": 10}, "headings": {"1": {"size": 18}}}),
        encoding="utf-8",
    )

    parsed = parse_write_options(
        [
            "input.md",
            "output.docx",
            "--style-config",
            str(config_path),
            "--body-size",
            "12",
            "--h1-size",
            "22",
        ]
    )

    assert parsed["body"]["size"] == 12
    assert parsed["headings"]["1"]["size"] == 22
