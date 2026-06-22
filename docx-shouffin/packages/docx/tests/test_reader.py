from pathlib import Path

from docx import Document

from main import docx_to_markdown


def test_docx_to_markdown_preserves_heading_and_formatting(tmp_path: Path):
    docx_path = tmp_path / "sample.docx"
    output_dir = tmp_path / "out"

    document = Document()
    document.add_heading("测试标题", level=1)
    paragraph = document.add_paragraph()
    paragraph.add_run("普通")
    bold_run = paragraph.add_run("加粗")
    bold_run.bold = True
    italic_run = paragraph.add_run("斜体")
    italic_run.italic = True
    document.save(docx_path)

    markdown = docx_to_markdown(str(docx_path), output_dir)

    assert "# 测试标题" in markdown
    assert "**加粗**" in markdown
    assert "*斜体*" in markdown


def test_handle_read_command_missing_file_returns_1(tmp_path, capsys):
    from main import handle_read_command

    assert handle_read_command(str(tmp_path / "nope.docx"), str(tmp_path / "out")) == 1
    assert "not found" in capsys.readouterr().err.lower()


def test_handle_read_command_non_docx_returns_1(tmp_path, capsys):
    from main import handle_read_command

    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    assert handle_read_command(str(tmp_path / "f.txt"), str(tmp_path / "out")) == 1
