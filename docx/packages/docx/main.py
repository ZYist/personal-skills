#!/usr/bin/env python3
import argparse
import json
import sys
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from markdown_it import MarkdownIt
from markdown_it.token import Token

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}

PAGE_SIZE_A4 = (Cm(21.0), Cm(29.7))

DEFAULT_STYLE = {
    "page": {
        "size": "A4",
        "margin_top": 2.54,
        "margin_bottom": 2.54,
        "margin_left": 3.18,
        "margin_right": 3.18,
    },
    "body": {
        "font": "Microsoft YaHei",
        "ascii_font": "Calibri",
        "size": 11,
        "line_spacing": 1.5,
        "space_after": 6,
    },
    "headings": {
        "1": {"font": "Microsoft YaHei", "size": 20, "bold": True},
        "2": {"font": "Microsoft YaHei", "size": 18, "bold": True},
        "3": {"font": "Microsoft YaHei", "size": 16, "bold": True},
        "4": {"font": "Microsoft YaHei", "size": 14, "bold": True},
        "5": {"font": "Microsoft YaHei", "size": 13, "bold": True},
        "6": {"font": "Microsoft YaHei", "size": 12, "bold": True},
    },
    "blockquote": {
        "font": "Microsoft YaHei",
        "ascii_font": "Calibri",
        "size": 11,
        "italic": True,
        "left_indent": 0.74,
        "space_after": 6,
    },
    "code_inline": {
        "font": "Consolas",
        "size": 10,
        "background_color": "F3F3F3",
    },
    "code_block": {
        "font": "Consolas",
        "size": 10,
        "background_color": "F3F3F3",
        "space_after": 6,
    },
    "table": {
        "header_bold": True,
        "header_bg_color": "D9EAF7",
        "border": True,
    },
    "image": {
        "max_width_inches": 5.8,
    },
}


def format_paragraph_text(paragraph) -> str:
    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        bold = run.bold
        italic = run.italic
        strike = run.font.strike if run.font else None
        underline = run.underline

        if bold and italic:
            text = f"***{text}***"
        elif bold:
            text = f"**{text}**"
        elif italic:
            text = f"*{text}*"

        if strike:
            text = f"~~{text}~~"
        if underline:
            text = f"<u>{text}</u>"

        parts.append(text)

    return "".join(parts)


def heading_level(paragraph) -> int | None:
    style_name = paragraph.style.name if paragraph.style else ""
    if style_name.startswith("Heading"):
        try:
            return int(style_name.replace("Heading", "").strip())
        except ValueError:
            return None
    return None


def table_to_markdown(table) -> str:
    if not table.rows:
        return ""

    lines = []
    for row_idx, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            cell_text = cell.text.strip().replace("\n", " ").replace("|", "\\|")
            cells.append(cell_text if cell_text else " ")
        lines.append("| " + " | ".join(cells) + " |")

        if row_idx == 0:
            lines.append("| " + " | ".join("---" for _ in cells) + " |")

    return "\n".join(lines)


def extract_images_and_attachments(docx_path: str, assets_dir: Path) -> list[str]:
    extracted = []
    docx_file = Path(docx_path)
    assets_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(docx_file, "r") as zf:
        attachment_extensions = {
            ".xlsx",
            ".xls",
            ".pptx",
            ".ppt",
            ".pdf",
            ".doc",
            ".docx",
            ".zip",
            ".rar",
            ".csv",
            ".txt",
        }

        for entry in zf.namelist():
            name = Path(entry)
            ext = name.suffix.lower()

            if name.parent.name == "media" and "word" in entry.split("/"):
                out_path = assets_dir / name.name
            elif ext in attachment_extensions and "embeddings" in entry.split("/"):
                out_path = assets_dir / name.name
            else:
                continue

            if out_path.exists():
                stem = out_path.stem
                counter = 1
                while out_path.exists():
                    out_path = assets_dir / f"{stem}_{counter}{ext}"
                    counter += 1

            data = zf.read(entry)
            out_path.write_bytes(data)
            extracted.append(str(out_path))

    return extracted


def build_image_map(docx_path: str) -> dict[str, str]:
    image_map: dict[str, str] = {}
    docx_file = Path(docx_path)

    with zipfile.ZipFile(docx_file, "r") as zf:
        if "word/_rels/document.xml.rels" not in zf.namelist():
            return image_map

        rels_xml = zf.read("word/_rels/document.xml.rels")
        root = ET.fromstring(rels_xml)

        for rel in root:
            rid = rel.get("Id", "")
            target = rel.get("Target", "")
            rel_type = rel.get("Type", "")

            if any(t in rel_type for t in ("image", "oleObject")):
                if target.startswith("/"):
                    target = target.lstrip("/")
                elif not target.startswith("word/"):
                    target = "word/" + target

                target_name = Path(target).name
                image_map[rid] = target_name

    return image_map


def get_inline_images(
    paragraph, image_map: dict[str, str], assets_name: str
) -> list[str]:
    refs = []
    p_elem = paragraph._element

    for drawing in p_elem.findall(".//w:drawing", NS):
        blip = drawing.find(".//a:blip", NS)
        if blip is None:
            for imagedata in drawing.findall(".//", NS):
                src = imagedata.get("src", "")
                if src and src in image_map:
                    filename = image_map[src]
                    refs.append(f"![{filename}]({assets_name}/{filename})")
            continue

        rid = blip.get(f"{{{NS['r']}}}embed", "")
        if rid and rid in image_map:
            filename = image_map[rid]
            refs.append(f"![{filename}]({assets_name}/{filename})")

    return refs


def extract_metadata(doc: Document, docx_path: str) -> str:
    props = doc.core_properties
    lines = ["---"]

    if props.title:
        lines.append(f'title: "{props.title}"')
    if props.author:
        lines.append(f'author: "{props.author}"')
    if props.created:
        lines.append(f'created: "{props.created.isoformat()}"')
    if props.modified:
        lines.append(f'modified: "{props.modified.isoformat()}"')
    if props.subject:
        lines.append(f'subject: "{props.subject}"')
    if props.keywords:
        lines.append(f'keywords: "{props.keywords}"')
    if props.category:
        lines.append(f'category: "{props.category}"')

    lines.append(f'source: "{Path(docx_path).name}"')
    lines.append("---")

    return "\n".join(lines)


def docx_to_markdown(docx_path: str, output_dir: Path) -> str:
    doc = Document(docx_path)
    docx_name = Path(docx_path).stem
    assets_name = docx_name
    assets_dir = output_dir / assets_name

    extract_images_and_attachments(docx_path, assets_dir)
    image_map = build_image_map(docx_path)

    md_lines = []

    metadata = extract_metadata(doc, docx_path)
    md_lines.append(metadata)
    md_lines.append("")

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "tbl":
            for table in doc.tables:
                if table._element is element:
                    md_lines.append(table_to_markdown(table))
                    md_lines.append("")
                    break
            continue

        if tag != "p":
            continue

        for paragraph in doc.paragraphs:
            if paragraph._element is not element:
                continue

            text = paragraph.text.strip()
            fmt_text = format_paragraph_text(paragraph)

            inline_images = get_inline_images(paragraph, image_map, assets_name)

            level = heading_level(paragraph)
            if level is not None:
                md_lines.append(f"{'#' * level} {fmt_text}")
                md_lines.append("")
            elif paragraph.style and "List" in (paragraph.style.name or ""):
                prefix = "- "
                if fmt_text.startswith(prefix):
                    md_lines.append(fmt_text)
                else:
                    md_lines.append(f"- {fmt_text}")
                md_lines.append("")
            elif not text and inline_images:
                for img in inline_images:
                    md_lines.append(img)
                    md_lines.append("")
            elif not text:
                md_lines.append("")
            else:
                alignment = paragraph.alignment
                if alignment == WD_ALIGN_PARAGRAPH.CENTER:
                    md_lines.append(f'<div align="center">{fmt_text}</div>')
                elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
                    md_lines.append(f'<div align="right">{fmt_text}</div>')
                else:
                    md_lines.append(fmt_text)
                md_lines.append("")

            if text and inline_images:
                for img in inline_images:
                    md_lines.append(img)
                    md_lines.append("")

            break

    result = "\n".join(md_lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip() + "\n"


def merge_style_config(defaults: dict, overrides: dict) -> dict:
    merged = deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_style_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_markdown_parser() -> MarkdownIt:
    return (
        MarkdownIt("commonmark", {"breaks": True})
        .enable("table")
        .enable("strikethrough")
    )


def set_run_fonts(run, font_name: str, ascii_font: str | None = None) -> None:
    run.font.name = ascii_font or font_name
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), ascii_font or font_name)
    r_fonts.set(qn("w:hAnsi"), ascii_font or font_name)
    r_fonts.set(qn("w:eastAsia"), font_name)


def set_run_shading(run, fill: str) -> None:
    r_pr = run._element.get_or_add_rPr()
    shading = r_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        r_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_paragraph_border(paragraph) -> None:
    p_pr = paragraph._element.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        p_pr.append(borders)
    bottom = borders.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        borders.append(bottom)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "BFBFBF")


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def apply_paragraph_style(paragraph, config: dict) -> None:
    paragraph_format = paragraph.paragraph_format
    if "line_spacing" in config:
        paragraph_format.line_spacing = config["line_spacing"]
    if "space_after" in config:
        paragraph_format.space_after = Pt(config["space_after"])
    if "left_indent" in config:
        paragraph_format.left_indent = Inches(config["left_indent"])


def add_styled_run(paragraph, text: str, style_state: dict, config: dict):
    run = paragraph.add_run(text)
    font_name = config.get("font", DEFAULT_STYLE["body"]["font"])
    ascii_font = config.get("ascii_font", DEFAULT_STYLE["body"]["ascii_font"])
    size = config.get("size", DEFAULT_STYLE["body"]["size"])
    set_run_fonts(run, font_name, ascii_font)
    run.font.size = Pt(size)
    run.bold = style_state.get("bold") or False
    run.italic = style_state.get("italic") or False
    run.font.strike = style_state.get("strike") or False
    if style_state.get("underline"):
        run.underline = True
    if style_state.get("link"):
        run.underline = True
        run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
    if style_state.get("code"):
        set_run_fonts(run, config["code_inline"]["font"], config["code_inline"]["font"])
        run.font.size = Pt(config["code_inline"]["size"])
        set_run_shading(run, config["code_inline"]["background_color"])
    return run


def find_matching_token(
    tokens: list[Token], start: int, open_type: str, close_type: str
) -> int:
    depth = 1
    index = start + 1
    while index < len(tokens):
        token = tokens[index]
        if token.type == open_type:
            depth += 1
        elif token.type == close_type:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError(f"Missing closing token for {open_type}")


def render_inline_tokens(
    paragraph,
    tokens: list[Token],
    config: dict,
    markdown_path: Path,
    style_state: dict | None = None,
) -> None:
    state = style_state or {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "text":
            add_styled_run(paragraph, token.content, state, config)
        elif token.type == "softbreak":
            paragraph.add_run().add_break(WD_BREAK.LINE)
        elif token.type == "hardbreak":
            paragraph.add_run().add_break(WD_BREAK.LINE)
        elif token.type == "code_inline":
            add_styled_run(paragraph, token.content, {**state, "code": True}, config)
        elif token.type == "image":
            src = token.attrGet("src") or ""
            image_path = (
                (markdown_path.parent / src).resolve()
                if not Path(src).is_absolute()
                else Path(src)
            )
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            paragraph.add_run().add_picture(
                str(image_path), width=Inches(config["image"]["max_width_inches"])
            )
        elif token.type in {"strong_open", "em_open", "s_open", "link_open"}:
            close_type = token.type.replace("_open", "_close")
            end = find_matching_token(tokens, index, token.type, close_type)
            nested_state = dict(state)
            if token.type == "strong_open":
                nested_state["bold"] = True
            elif token.type == "em_open":
                nested_state["italic"] = True
            elif token.type == "s_open":
                nested_state["strike"] = True
            elif token.type == "link_open":
                nested_state["link"] = True
            render_inline_tokens(
                paragraph,
                tokens[index + 1 : end],
                config,
                markdown_path,
                nested_state,
            )
            index = end
        index += 1


def collect_table_rows(
    tokens: list[Token], start: int
) -> tuple[list[list[list[Token]]], int]:
    rows: list[list[list[Token]]] = []
    index = start + 1
    current_row: list[list[Token]] = []

    while index < len(tokens):
        token = tokens[index]
        if token.type == "table_close":
            if current_row:
                rows.append(current_row)
            return rows, index
        if token.type == "tr_open":
            current_row = []
        elif token.type in {"th_open", "td_open"}:
            inline_token = tokens[index + 1]
            current_row.append(inline_token.children or [])
        elif token.type == "tr_close":
            rows.append(current_row)
            current_row = []
        index += 1

    raise ValueError("Unclosed table token")


def add_table(
    document: Document, rows: list[list[list[Token]]], config: dict, markdown_path: Path
) -> None:
    if not rows:
        return
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for row_index, row in enumerate(rows):
        for cell_index, cell_tokens in enumerate(row):
            cell = table.cell(row_index, cell_index)
            paragraph = cell.paragraphs[0]
            paragraph.clear()
            apply_paragraph_style(paragraph, config["body"])
            render_inline_tokens(paragraph, cell_tokens, config, markdown_path)
            if row_index == 0:
                for run in paragraph.runs:
                    run.bold = config["table"].get("header_bold", True)
                set_cell_shading(cell, config["table"]["header_bg_color"])


def configure_document(document: Document, config: dict) -> None:
    section = document.sections[0]
    section.start_type = WD_SECTION.NEW_PAGE
    if config["page"].get("size") == "A4":
        section.page_width, section.page_height = PAGE_SIZE_A4
    section.top_margin = Cm(config["page"]["margin_top"])
    section.bottom_margin = Cm(config["page"]["margin_bottom"])
    section.left_margin = Cm(config["page"]["margin_left"])
    section.right_margin = Cm(config["page"]["margin_right"])


def markdown_to_docx(
    markdown_path: Path, output_path: Path, style_config: dict | None = None
) -> None:
    config = merge_style_config(DEFAULT_STYLE, style_config or {})
    parser = build_markdown_parser()
    tokens = parser.parse(markdown_path.read_text(encoding="utf-8"))
    document = Document()
    configure_document(document, config)

    list_style: str | None = None
    blockquote_depth = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open":
            level = int(token.tag[1])
            inline_token = tokens[index + 1]
            paragraph = document.add_heading(level=level)
            paragraph.clear()
            apply_paragraph_style(paragraph, config["body"])
            render_inline_tokens(
                paragraph, inline_token.children or [], config, markdown_path
            )
            heading_config = config["headings"][str(level)]
            for run in paragraph.runs:
                set_run_fonts(
                    run,
                    heading_config["font"],
                    config["body"].get("ascii_font", heading_config["font"]),
                )
                run.font.size = Pt(heading_config["size"])
                run.bold = heading_config.get("bold", True)
            index += 2
        elif token.type == "paragraph_open":
            inline_token = tokens[index + 1]
            style_name = list_style or "Normal"
            paragraph = document.add_paragraph(style=style_name)
            paragraph.clear()
            paragraph_config = (
                config["blockquote"] if blockquote_depth else config["body"]
            )
            apply_paragraph_style(paragraph, paragraph_config)
            render_inline_tokens(
                paragraph, inline_token.children or [], config, markdown_path
            )
            if blockquote_depth:
                for run in paragraph.runs:
                    run.italic = config["blockquote"].get("italic", False) or run.italic
            index += 2
        elif token.type == "bullet_list_open":
            list_style = "List Bullet"
        elif token.type == "ordered_list_open":
            list_style = "List Number"
        elif token.type in {"bullet_list_close", "ordered_list_close"}:
            list_style = None
        elif token.type == "blockquote_open":
            blockquote_depth += 1
        elif token.type == "blockquote_close":
            blockquote_depth = max(0, blockquote_depth - 1)
        elif token.type in {"fence", "code_block"}:
            paragraph = document.add_paragraph()
            apply_paragraph_style(paragraph, config["code_block"])
            run = paragraph.add_run(token.content.rstrip("\n"))
            set_run_fonts(
                run, config["code_block"]["font"], config["code_block"]["font"]
            )
            run.font.size = Pt(config["code_block"]["size"])
            set_run_shading(run, config["code_block"]["background_color"])
        elif token.type == "hr":
            paragraph = document.add_paragraph()
            set_paragraph_border(paragraph)
        elif token.type == "table_open":
            rows, end_index = collect_table_rows(tokens, index)
            add_table(document, rows, config, markdown_path)
            index = end_index
        index += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def build_style_overrides(args: argparse.Namespace) -> dict:
    overrides: dict = {}
    if args.style_config:
        config_path = Path(args.style_config)
        if not config_path.exists():
            raise FileNotFoundError(f"Style config not found: {config_path}")
        overrides = json.loads(config_path.read_text(encoding="utf-8"))

    if args.body_font or args.body_size:
        overrides.setdefault("body", {})
    if args.body_font:
        overrides["body"]["font"] = args.body_font
    if args.body_size:
        overrides["body"]["size"] = args.body_size

    for level in (1, 2, 3, 4, 5, 6):
        font_value = getattr(args, f"h{level}_font")
        size_value = getattr(args, f"h{level}_size")
        if font_value or size_value:
            overrides.setdefault("headings", {})
            overrides["headings"].setdefault(str(level), {})
        if font_value:
            overrides["headings"][str(level)]["font"] = font_value
        if size_value:
            overrides["headings"][str(level)]["size"] = size_value

    if args.image_max_width:
        overrides.setdefault("image", {})
        overrides["image"]["max_width_inches"] = args.image_max_width

    return merge_style_config(DEFAULT_STYLE, overrides)


def parse_write_options(argv: list[str]) -> dict:
    parser = argparse.ArgumentParser(prog="main.py write")
    parser.add_argument("input_md")
    parser.add_argument("output_docx", nargs="?")
    parser.add_argument("--style-config")
    parser.add_argument("--body-font")
    parser.add_argument("--body-size", type=float)
    for level in (1, 2, 3, 4, 5, 6):
        parser.add_argument(f"--h{level}-font")
        parser.add_argument(f"--h{level}-size", type=float)
    parser.add_argument("--image-max-width", type=float)
    args = parser.parse_args(argv)
    return build_style_overrides(args)


def handle_read_command(file_path: str, output_dir: str | None) -> int:
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    if path.suffix.lower() != ".docx":
        print(
            f"Error: Unsupported format: {path.suffix}. Only .docx is supported.",
            file=sys.stderr,
        )
        return 1

    out = Path(output_dir) if output_dir else Path.cwd() / "docs" / "extracted"
    out.mkdir(parents=True, exist_ok=True)

    md_content = docx_to_markdown(str(path), out)
    md_file = out / f"{path.stem}.md"
    md_file.write_text(md_content, encoding="utf-8")

    assets_dir = out / path.stem
    asset_count = 0
    if assets_dir.exists():
        asset_count = len([file for file in assets_dir.iterdir() if file.is_file()])

    print(f"Success: {path.name}")
    print(f"Markdown: {md_file}")
    if asset_count > 0:
        print(f"Assets: {assets_dir} ({asset_count} files)")
    return 0


def handle_write_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="main.py write")
    parser.add_argument("input_md")
    parser.add_argument("output_docx", nargs="?")
    parser.add_argument("--style-config")
    parser.add_argument("--body-font")
    parser.add_argument("--body-size", type=float)
    for level in (1, 2, 3, 4, 5, 6):
        parser.add_argument(f"--h{level}-font")
        parser.add_argument(f"--h{level}-size", type=float)
    parser.add_argument("--image-max-width", type=float)
    args = parser.parse_args(argv)

    input_md = Path(args.input_md)
    if not input_md.exists():
        print(f"Error: File not found: {input_md}", file=sys.stderr)
        return 1
    if input_md.suffix.lower() != ".md":
        print(
            f"Error: Unsupported format: {input_md.suffix}. Only .md is supported.",
            file=sys.stderr,
        )
        return 1

    output_docx = (
        Path(args.output_docx) if args.output_docx else input_md.with_suffix(".docx")
    )
    style = build_style_overrides(args)
    markdown_to_docx(input_md, output_docx, style)
    print(f"Success: {output_docx}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python main.py <docx_file> [output_dir]", file=sys.stderr)
        print(
            "       python main.py write <input.md> [output.docx] [options]",
            file=sys.stderr,
        )
        return 1

    try:
        if sys.argv[1] == "write":
            return handle_write_command(sys.argv[2:])
        return handle_read_command(
            sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
